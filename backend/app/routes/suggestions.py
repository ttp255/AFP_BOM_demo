import uuid

from fastapi import APIRouter, HTTPException

from app.db.supabase_client import supabase
from app.services.approval_service import approve_suggestion, reject_suggestion
from app.services.pipeline_service import (
    suggest_products_for_bom_item,
    suggest_products_for_project,
)
from app.services.suggestion_constants import PRODUCT_SUGGESTION_LIMIT

router = APIRouter()


@router.get("/projects/{project_id}")
def list_suggestions(project_id: str):
    try:
        uuid.UUID(project_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail=f"Invalid project_id: '{project_id}' is not a valid UUID")
    bom_items = supabase.table("afp_bom_items").select("*").eq("project_id", project_id).execute().data
    bom_by_id = {item["id"]: item for item in bom_items}
    elements = supabase.table("afp_revit_elements").select("*").eq("project_id", project_id).execute().data
    element_by_id = {element["id"]: element for element in elements}
    suggestions = supabase.table("afp_bom_product_suggestions").select("*").execute().data
    project_suggestions = [
        suggestion
        for suggestion in suggestions
        if suggestion.get("bom_item_id") in bom_by_id
        and 1 <= (suggestion.get("rank_no") or 0) <= PRODUCT_SUGGESTION_LIMIT
    ]
    products = supabase.table("afp_products").select("*").execute().data
    suppliers = supabase.table("afp_suppliers").select("*").execute().data
    offers = supabase.table("afp_product_suppliers").select("*").execute().data
    product_by_id = {product["id"]: product for product in products}
    supplier_by_id = {supplier["id"]: supplier for supplier in suppliers}
    offer_by_id = {offer["id"]: offer for offer in offers}
    offer_by_product_supplier = {
        (offer.get("product_id"), offer.get("supplier_id")): offer
        for offer in offers
        if offer.get("product_id") is not None and offer.get("supplier_id") is not None
    }

    result = []
    for suggestion in project_suggestions:
        offer = offer_by_id.get(suggestion.get("product_supplier_id"))
        if offer is None:
            offer = offer_by_product_supplier.get(
                (suggestion.get("product_id"), suggestion.get("supplier_id"))
            )

        estimated_total_cost = suggestion.get("estimated_total_cost")
        if offer and offer.get("unit_price") is not None:
            package_qty = suggestion.get("estimated_required_package_qty")
            if package_qty is not None:
                estimated_total_cost = float(package_qty) * float(offer["unit_price"])

        result.append({
            **suggestion,
            "suggestion_status": suggestion.get("suggestion_status") or suggestion.get("status"),
            "estimated_total_cost": (
                estimated_total_cost
                if estimated_total_cost is not None
                else suggestion.get("total_cost")
            ),
            "currency": (offer or {}).get("currency") or suggestion.get("currency") or "VND",
            "note": suggestion.get("note") or suggestion.get("reason"),
            "bom_item": bom_by_id.get(suggestion.get("bom_item_id")),
            "element": element_by_id.get(
                (bom_by_id.get(suggestion.get("bom_item_id")) or {}).get("revit_element_id")
            ),
            "product": product_by_id.get(suggestion.get("product_id")),
            "supplier": supplier_by_id.get(suggestion.get("supplier_id")),
            "offer": offer,
        })
    return sorted(result, key=lambda item: (
        item.get("bom_item_id") or 0, item.get("rank_no") or 999,
    ))


@router.post("/projects/{project_id}/suggest")
def suggest_products(project_id: str):
    suggestions = suggest_products_for_project(project_id, enrich_with_ai=True)
    return {
        "project_id": project_id,
        "suggestions_count": len(suggestions),
        "suggestions": suggestions,
    }


@router.post("/bom-items/{bom_item_id}/suggest")
def suggest_bom_item(bom_item_id: str):
    bom_item = (
        supabase.table("afp_bom_items").select("*").eq("id", bom_item_id)
        .single().execute().data
    )
    if not bom_item:
        raise HTTPException(status_code=404, detail="BOM item not found")
    try:
        suggestions = suggest_products_for_bom_item(bom_item)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "bom_item_id": bom_item_id,
        "suggestions": suggestions,
    }

@router.post("/{suggestion_id}/approve")
def approve(suggestion_id: str):
    try:
        return approve_suggestion(suggestion_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{suggestion_id}/reject")
def reject(suggestion_id: str):
    try:
        return reject_suggestion(suggestion_id)
    except ValueError as exc:
        status_code = 409 if "Approved" in str(exc) else 404
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


