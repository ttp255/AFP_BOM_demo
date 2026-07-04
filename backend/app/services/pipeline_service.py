import re

from postgrest.exceptions import APIError

from app.db.supabase_client import supabase
from app.services.product_matcher import filter_products
from app.services.llm_bom_service import (
    clean_catalog_language,
    describe_feature_outcomes,
    explain_ranked_candidates,
)
from app.services.ranking_service import rank_products_for_bom_item
from app.services.requirement_service import build_requirement_for_bom_item
from app.services.vector_service import semantic_product_ids
from app.services.bom_status_service import set_bom_suggestion_status
from app.services.suggestion_constants import PRODUCT_SUGGESTION_LIMIT

def _evidence_based_reason(item: dict, requirement: dict) -> str:
    """Build a natural, evidence-only fallback when the LLM is unavailable."""
    product = item["product"]
    wanted = (requirement.get("required_features") or []) + (requirement.get("preferred_features") or [])
    matched = [feature for feature in wanted if feature in (product.get("features") or [])]
    effective_reason = clean_catalog_language(product.get("effective_reason"))
    effective_reason = effective_reason[:1].upper() + effective_reason[1:]

    usage_area = str(requirement.get("usage_area") or "").strip().casefold()
    need_by_area = {
        "interior_wall": (
            "Đối với tường nội thất, ưu tiên là bề mặt hoàn thiện ổn định, "
            "thuận tiện khi thi công và bảo trì sau bàn giao."
        ),
        "exterior_wall": (
            "Đối với tường ngoài trời, lớp hoàn thiện cần chịu được tác động "
            "của thời tiết và duy trì khả năng bảo vệ bề mặt."
        ),
        "wet_area": (
            "Ở khu vực thường xuyên ẩm, cần ưu tiên khả năng bảo vệ nền và "
            "hạn chế các vấn đề phát sinh do độ ẩm."
        ),
        "decorative_feature_wall": (
            "Với mảng tường nhấn, điều quan trọng là chuẩn bị nền đúng hệ "
            "để lớp hoàn thiện bám chắc và thể hiện hiệu ứng đồng đều."
        ),
    }
    project_need = need_by_area.get(
        usage_area,
        "Với hạng mục này, cần ưu tiên giải pháp phù hợp điều kiện bề mặt và thuận tiện trong quá trình sử dụng.",
    )
    if effective_reason:
        return f"{project_need} {effective_reason}"
    if matched:
        outcomes = describe_feature_outcomes(matched[:3])
        if outcomes:
            return f"{project_need} " + "; ".join(outcomes).capitalize() + "."
        return (
            f"{project_need} Cần đối chiếu datasheet để xác nhận chức năng và "
            "mức hiệu năng cụ thể của sản phẩm."
        )
    return (
        f"{project_need} Hiện chưa đủ dữ liệu để xác nhận lợi ích kỹ thuật; "
        "cần kiểm tra datasheet và điều kiện bề mặt trước khi phê duyệt."
    )

def _evidence_based_explanation(item: dict, requirement: dict) -> dict:
    """Return the same JSON shape when the LLM response cannot be accepted."""
    reason = _evidence_based_reason(item, requirement)
    summary, separator, detail = reason.partition(". ")
    summary = summary.rstrip(".") + "."
    explanation = detail if separator else reason
    return {
        "summary": summary,
        "explanation": explanation,
        "main_reasons": [],
        "not_needed_products": "",
        "approval_recommendation": (
            "Có thể đưa vào phương án đề xuất; cần đối chiếu datasheet và "
            "xác nhận điều kiện bề mặt trước khi phê duyệt."
        ),
    }

def _refresh_existing_explanations(
    existing: list[dict], ranked: list[dict], requirement: dict,
) -> list[dict]:
    """Refresh narrative fields without changing an approved selection."""
    ranked_by_product = {
        item["product"]["id"]: item for item in ranked[:PRODUCT_SUGGESTION_LIMIT]
    }
    existing_product_ids = {row.get("product_id") for row in existing}
    catalog_products = supabase.table("afp_products").select("*").execute().data
    for product in catalog_products:
        if product.get("id") in existing_product_ids:
            ranked_by_product.setdefault(product["id"], {"product": product})
    refreshed = []
    for row in existing:
        item = ranked_by_product.get(row.get("product_id"))
        if item is None:
            refreshed.append(row)
            continue
        values = {
            "explanation": item.get("llm_explanation") or _evidence_based_explanation(item, requirement),
            "note": item.get("llm_reason") or _evidence_based_reason(item, requirement),
        }
        try:
            result = (
                supabase.table("afp_bom_product_suggestions")
                .update(values)
                .eq("id", row["id"])
                .execute()
                .data
            )
        except APIError as exc:
            if exc.code != "PGRST204" or "explanation" not in (exc.message or ""):
                raise
            values.pop("explanation", None)
            result = (
                supabase.table("afp_bom_product_suggestions")
                .update(values)
                .eq("id", row["id"])
                .execute()
                .data
            )
        refreshed.append((result or [{**row, **values}])[0])
    return refreshed

def suggest_products_for_project(project_id: str, *, enrich_with_ai: bool = True) -> list[dict]:
    bom_items = (
        supabase.table("afp_bom_items")
        .select("*")
        .eq("project_id", project_id)
        .execute()
        .data
    )

    all_suggestions = []
    for bom_item in bom_items:
        try:
            all_suggestions.extend(
                suggest_products_for_bom_item(bom_item, enrich_with_ai=enrich_with_ai)
            )
        except Exception:
            # One malformed BOM item must not abort the whole project.
            continue
    return all_suggestions


def suggest_products_for_bom_item(
    bom_item: dict, *, enrich_with_ai: bool = True,
) -> list[dict]:
    """Run the complete, constrained pipeline for exactly one BOM item."""
    requirement = build_requirement_for_bom_item(bom_item)
    semantic_scores = (
        semantic_product_ids(requirement, bom_item) if enrich_with_ai else {}
    )
    products = filter_products(requirement, semantic_scores)
    ranked = rank_products_for_bom_item(bom_item, products, requirement)
    if enrich_with_ai:
        ranked = explain_ranked_candidates(bom_item, requirement, ranked)
    return save_suggestions(bom_item, ranked, requirement)


def save_suggestions(
    bom_item: dict,
    ranked: list[dict],
    requirement: dict,
    limit: int = PRODUCT_SUGGESTION_LIMIT,
) -> list[dict]:
    existing = (
        supabase.table("afp_bom_product_suggestions")
        .select("*")
        .eq("bom_item_id", bom_item["id"])
        .execute()
        .data
    )
    if any(row.get("suggestion_status") == "approved" for row in existing):
        existing = _refresh_existing_explanations(existing, ranked, requirement)
        set_bom_suggestion_status(bom_item["id"], "approved")
        return existing
    if existing:
        supabase.table("afp_bom_product_suggestions").delete().eq(
            "bom_item_id", bom_item["id"]
        ).execute()

    if not ranked:
        set_bom_suggestion_status(bom_item["id"], "pending")
        return []

    rows = []
    for index, item in enumerate(ranked[:limit], start=1):
        product = item["product"]
        supplier_row = item["supplier_row"]
        score = item["score"]
        row = {
            "bom_item_id": bom_item["id"],
            "product_id": product["id"],
            "supplier_id": supplier_row["supplier_id"],
            "product_supplier_id": supplier_row.get("id"),
            "rank_no": index,
            "is_best_option": index == 1,
            "hard_filter_pass": True,
            "required_match": {
                "product_type": requirement.get("required_product_type"),
                "tags": requirement.get("required_tags") or [],
                "features": requirement.get("required_features") or [],
            },
            "preferred_match": {
                "features": requirement.get("preferred_features") or [],
            },
            "feature_score": score["feature_score"],
            "semantic_score": score["semantic_score"],
            "price_score": score["price_score"],
            "stock_score": score["stock_score"],
            "delivery_score": score["delivery_score"],
            "supplier_score": score["supplier_score"],
            "final_score": score["final_score"],
            "estimated_required_package_qty": item["package_qty"],
            "estimated_total_cost": item["total_cost"],
            "required_painted_area": item.get("required_painted_area"),
            "currency": supplier_row.get("currency") or "VND",
            "suggestion_status": "suggested",
            "explanation": item.get("llm_explanation") or _evidence_based_explanation(item, requirement),
            "note": item.get("llm_reason") or _evidence_based_reason(item, requirement),
        }
        rows.append(row)

    # Insert all candidates in one database round trip.
    try:
        result = supabase.table("afp_bom_product_suggestions").insert(rows).execute()
    except APIError as exc:
        # If the insert fails because a new column is not yet in the DB schema
        # (e.g. required_painted_area), retry without that optional column so
        # existing deployments continue to work until the migration is applied.
        missing_column = next(
            (
                column for column in ("required_painted_area", "explanation")
                if column in (exc.message or "")
            ),
            None,
        )
        if exc.code == "PGRST204" and missing_column:
            for row in rows:
                row.pop(missing_column, None)
            result = supabase.table("afp_bom_product_suggestions").insert(rows).execute()
        else:
            raise
    rows = result.data or []

    set_bom_suggestion_status(bom_item["id"], "suggested")

    return rows


