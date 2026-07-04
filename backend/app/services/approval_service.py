from datetime import datetime, timezone

from app.db.supabase_client import supabase
from app.services.bom_status_service import set_bom_suggestion_status


def approve_suggestion(suggestion_id: str, approved_by: str = "admin") -> dict:
    suggestion = (
        supabase.table("afp_bom_product_suggestions")
        .select("*")
        .eq("id", suggestion_id)
        .single()
        .execute()
        .data
    )
    if not suggestion:
        raise ValueError("Suggestion not found")

    bom_item_id = suggestion["bom_item_id"]
    supabase.table("afp_bom_product_suggestions").update({
        "suggestion_status": "rejected",
        "is_best_option": False,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("bom_item_id", bom_item_id).execute()

    supabase.table("afp_bom_product_suggestions").update({
        "suggestion_status": "approved",
        "is_best_option": True,
        "approved_by": approved_by,
        "approved_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", suggestion_id).execute()

    set_bom_suggestion_status(bom_item_id, "approved")
    return {"suggestion_id": suggestion_id, "bom_item_id": bom_item_id, "status": "approved"}


def reject_suggestion(suggestion_id: str) -> dict:
    suggestion = (
        supabase.table("afp_bom_product_suggestions").select("*")
        .eq("id", suggestion_id).single().execute().data
    )
    if not suggestion:
        raise ValueError("Suggestion not found")
    if suggestion.get("suggestion_status") == "approved":
        raise ValueError("Approved suggestions cannot be rejected; approve a replacement instead")

    supabase.table("afp_bom_product_suggestions").update({
        "suggestion_status": "rejected",
        "is_best_option": False,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", suggestion_id).execute()

    bom_item_id = suggestion["bom_item_id"]
    remaining = (
        supabase.table("afp_bom_product_suggestions").select("*")
        .eq("bom_item_id", bom_item_id).execute().data
    )
    status = "suggested" if any(
        row.get("suggestion_status") == "suggested" for row in remaining
    ) else "pending"
    set_bom_suggestion_status(bom_item_id, status)
    return {"suggestion_id": suggestion_id, "bom_item_id": bom_item_id, "status": "rejected"}



