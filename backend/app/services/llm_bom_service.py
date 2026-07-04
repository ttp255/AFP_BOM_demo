"""Constrained NVIDIA LLM explanations for already-ranked BOM candidates."""

from __future__ import annotations

import json
import re

from app.core.config import settings
from app.services.suggestion_constants import PRODUCT_SUGGESTION_LIMIT

EXPLANATION_STYLE = "consultant"

_CATALOG_LABELS = (
    (r"\bexterior wall paint\b", "sơn dùng cho tường ngoài trời"),
    (r"\binterior wall paint\b", "sơn dùng cho tường nội thất"),
    (r"\bexterior paint\b", "sơn ngoài trời"),
    (r"\binterior paint\b", "sơn nội thất"),
    (r"\bexterior wall\b", "tường ngoài trời"),
    (r"\binterior wall\b", "tường nội thất"),
    (r"\bexterior\b", "ngoài trời"),
    (r"\binterior\b", "nội thất"),
)

_FEATURE_OUTCOMES = {
    "uv_resistant": "giảm tác động của tia UV lên màng sơn, giúp màu sắc bền hơn khi phơi nắng",
    "water_resistant": "hạn chế nước thấm qua bề mặt, giúp tường ít bị xuống cấp do ẩm",
    "waterproof": "tạo lớp bảo vệ chống nước cho bề mặt",
    "color_retention": "duy trì màu sắc ổn định lâu hơn, giảm nhu cầu sơn lại sớm",
    "weather_resistant": "bảo vệ màng sơn trước nắng mưa và biến đổi thời tiết",
    "mold_resistant": "hạn chế nấm mốc phát triển trên bề mặt",
    "salt_air_resistant": "hạn chế ảnh hưởng của hơi muối lên lớp hoàn thiện",
    "easy_clean": "giúp vết bẩn dễ được làm sạch trong quá trình sử dụng",
    "low_voc": "giảm phát thải hợp chất hữu cơ bay hơi trong không gian sử dụng",
}


def describe_feature_outcomes(features: object) -> list[str]:
    """Convert supported catalog tags into user-centred, practical outcomes."""
    if not isinstance(features, (list, tuple)):
        return []
    return [_FEATURE_OUTCOMES[tag] for tag in features if tag in _FEATURE_OUTCOMES]


def clean_catalog_language(value: object) -> str:
    """Translate internal catalog labels before they reach user-facing prose."""
    text = " ".join(str(value or "").replace("_", " ").split())
    for pattern, replacement in _CATALOG_LABELS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    text = re.sub(r"^\s*Hiệu quả vì\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(
        r"\bDữ liệu sản phẩm cho biết\s*:\s*", "", text, flags=re.IGNORECASE,
    )
    return text.strip(" ,.;:-")


def _consultant_prompt(context: dict, payload: list[dict]) -> str:
    """Build natural explanations while preserving batch identifiers."""
    return (
        "You are a senior paint consultant for a Revit BOM product suggestion system.\n\n"
        "Write a natural Vietnamese explanation for every selected product.\n\n"
        f"Style:\n{EXPLANATION_STYLE}\n\n"
        "Rules:\n"
        "- Write every user-facing field entirely in natural Vietnamese.\n"
        "- Do not sound like database output.\n"
        "- Never output English catalog labels, including \"interior\", \"exterior\", \"interior wall paint\", and \"exterior wall paint\".\n"
        "- Describe the application naturally, for example \"tường ngoài trời\" or \"tường nội thất\"; do not expose product_type, recommended_for_tags, or features.\n"
        "- Do not say \"đáp ứng đúng mục đích sử dụng\".\n"
        "- Do not begin with \"Hiệu quả vì\".\n"
        "- Do not use meta phrases such as \"Dữ liệu sản phẩm cho biết\". State the supported benefit directly and explain its practical effect.\n"
        "- Do not copy product data directly or merely list features.\n"
        "- Never justify effectiveness merely by saying the product matches an area, category, surface, or has certain properties.\n"
        "- Emphasize what the product actually does: what it protects or improves, how that action addresses the exposure or condition, and the practical result for durability, appearance, or maintenance.\n"
        "- Turn each supported quality into a cause-and-effect statement. Example: UV protection reduces sun damage so the exterior finish keeps its colour longer; do not write it is effective because it has certain properties.\n"
        "- Start from the real project need: room, surface, condition, finish, or application constraint.\n"
        "- Connect only supported product benefits to that need and to a practical outcome.\n"
        "- Explain why unnecessary product types are not needed. Do not invent one; return an empty string when no useful exclusion is supported.\n"
        "- Keep it practical, specific, concise, and natural for an architect, QS, or project owner.\n"
        "- Use only supplied context. Do not invent performance, standards, comparisons, or alternatives.\n"
        "- Do not rerank products, change identifiers, mention scores, or repeat ideas across fields.\n"
        "- Each field has one job: summary states the need, explanation gives evidence, and approval_recommendation gives only the decision or verification action.\n"
        "- Never restate the summary or explanation in approval_recommendation, even with different wording.\n"
        "- If evidence is insufficient, state what must be verified in the datasheet or on site.\n\n"
        "Return valid JSON only, without Markdown or introductory text, in exactly this batch structure:\n"
        '{"explanations":[{"product_id":"...","element_id":"...","summary":"","explanation":"","main_reasons":[],"not_needed_products":"","approval_recommendation":""}]}.\n\n'
        "Field guidance:\n"
        "- summary: one short sentence beginning with the actual project need, not the product name.\n"
        "- explanation: lead with the product's function and describe the resulting protection, durability, appearance, or maintenance benefit for this project.\n"
        "- main_reasons: 1 to 3 distinct outcomes or functions in natural Vietnamese, never property names or catalog tags.\n"
        "- not_needed_products: briefly explain why a more specialized or unrelated coating is unnecessary; use an empty string when no defensible comparison exists.\n"
        "- approval_recommendation: give only the approval decision and any necessary verification condition; do not repeat why the product fits.\n\n"
        f"Project context: {json.dumps(context, ensure_ascii=False, default=str)}\n"
        f"Ranked selected products: {json.dumps(payload, ensure_ascii=False, default=str)}"
    )


def _clean_explanation_text(value: object) -> str:
    """Remove catalog labels and disallowed lead-ins from user-facing prose."""
    text = clean_catalog_language(value)
    text = re.sub(r"\bđáp ứng đúng mục đích sử dụng\b", "phù hợp với điều kiện sử dụng", text, flags=re.IGNORECASE)
    text = text.strip(" ,.;:-")
    return text[:1].upper() + text[1:]


def explain_ranked_candidates(
    bom_item: dict, requirement: dict, ranked: list[dict], limit: int = PRODUCT_SUGGESTION_LIMIT,
) -> list[dict]:
    """Explain known candidates only; never change rank or invent catalog data."""
    candidates = ranked[:limit]
    element_id = (
        bom_item.get("revit_element_id")
        or (bom_item.get("source_element_ids") or [None])[0]
    )
    if (
        settings.AFP_USE_MOCK_DB
        or not settings.NVIDIA_KEY
        or not settings.LLM_EXPLANATIONS_ENABLED
        or not candidates
    ):
        return ranked

    payload = [{
        "product_id": item["product"]["id"],
        "element_id": element_id,
        "bom_item": bom_item.get("item_name"),
        "room_type": bom_item.get("room_type"),
        "product_name": item["product"].get("product_name"),
        "product_category": (
            clean_catalog_language(item["product"].get("product_type"))
        ),
        "practical_product_outcomes": describe_feature_outcomes(
            item["product"].get("features") or []
        ),
        "suitable_surfaces": item["product"].get("surface_types") or [],
        "best_suited_for": item["product"].get("recommended_for_tags") or [],
        "not_suitable_for": item["product"].get("not_recommended_for_tags") or [],
        "applicable_areas": item["product"].get("usage_areas") or [],
        "product_function": item["product"].get("function_description"),
        "why_effective": clean_catalog_language(item["product"].get("effective_reason")),
        "coverage_m2_per_liter": item["product"].get("coverage_m2_per_liter"),
        "package_size": item["product"].get("package_size"),
        "packages_required": item["package_qty"],
        "estimated_cost": item["total_cost"],
        "currency": item["supplier_row"].get("currency") or "VND",
        "stock_qty": item["supplier_row"].get("stock_qty"),
        "delivery_days": item["supplier_row"].get("delivery_days"),
    } for item in candidates]
    context = {
        "element_id": element_id,
        "bom_item": bom_item.get("item_name"),
        "room_type": bom_item.get("room_type"),
        "surface": bom_item.get("surface"),
        "substrate": bom_item.get("substrate"),
        "condition": bom_item.get("condition"),
        "finish": bom_item.get("finish_type"),
        "required_product_category": (
            clean_catalog_language(requirement.get("required_product_type"))
        ),
        "usage_area": clean_catalog_language(requirement.get("usage_area")),
        "required_practical_outcomes": describe_feature_outcomes(
            requirement.get("required_features") or []
        ),
        "preferred_practical_outcomes": describe_feature_outcomes(
            requirement.get("preferred_features") or []
        ),
    }
    prompt = _consultant_prompt(context, payload)
    try:
        from langchain_nvidia_ai_endpoints import ChatNVIDIA
        response = ChatNVIDIA(
            model=settings.LLM_MODEL, api_key=settings.NVIDIA_KEY, temperature=0.0, timeout=60.0,
        ).invoke(prompt)
        content = response.content if isinstance(response.content, str) else str(response.content)
        content = content.strip()
        if content.startswith("```"):
            content = content.removeprefix("```json").removeprefix("```JSON")
            content = content.removeprefix("```").removesuffix("```").strip()
        choices = json.loads(content).get("explanations", [])
    except Exception:
        return ranked

    by_id = {item["product"]["id"]: item for item in candidates}
    expected_ids = set(by_id)
    choice_ids = [choice.get("product_id") for choice in choices]
    if (
        len(choice_ids) != len(expected_ids)
        or len(set(choice_ids)) != len(choice_ids)
        or set(choice_ids) != expected_ids
    ):
        return ranked

    for choice in choices:
        if str(choice.get("element_id")) != str(element_id):
            return ranked
        item = by_id.get(choice.get("product_id"))
        if item is None:
            return ranked
        explanation = {
            "summary": _clean_explanation_text(choice.get("summary")),
            "explanation": _clean_explanation_text(choice.get("explanation")),
            "main_reasons": [_clean_explanation_text(value) for value in (choice.get("main_reasons") or []) if _clean_explanation_text(value)],
            "not_needed_products": _clean_explanation_text(choice.get("not_needed_products")),
            "approval_recommendation": _clean_explanation_text(choice.get("approval_recommendation")),
        }
        if not explanation["summary"] or not explanation["explanation"] or not explanation["main_reasons"]:
            return ranked
        if not explanation["approval_recommendation"]:
            return ranked
        normalized_parts = [
            value.casefold().strip(" .,:;")
            for value in [
                explanation["summary"],
                explanation["explanation"],
                *explanation["main_reasons"],
                explanation["not_needed_products"],
                explanation["approval_recommendation"],
            ]
            if value
        ]
        if len(normalized_parts) != len(set(normalized_parts)):
            return ranked
        explanation_text = json.dumps(explanation, ensure_ascii=False)
        if any(marker in explanation_text for marker in ("Ã", "Â", "á»", "áº")):
            return ranked
        by_id.pop(choice["product_id"])
        item["llm_explanation"] = explanation
        item["llm_reason"] = " ".join([explanation["summary"], explanation["explanation"]])
    return ranked



def rerank_candidates(
    bom_item: dict, requirement: dict, ranked: list[dict], limit: int = PRODUCT_SUGGESTION_LIMIT,
) -> list[dict]:
    """Backward-compatible alias for the former rerank step."""
    return explain_ranked_candidates(bom_item, requirement, ranked, limit)






