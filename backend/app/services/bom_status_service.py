from postgrest.exceptions import APIError

from app.db.supabase_client import supabase


def set_bom_suggestion_status(bom_item_id: str, status: str) -> None:
    """Persist workflow state on current and legacy AFP schemas."""
    try:
        (
            supabase.table("afp_bom_items")
            .update({"suggestion_status": status})
            .eq("id", bom_item_id)
            .execute()
        )
    except APIError as exc:
        if exc.code != "PGRST204" or "suggestion_status" not in str(exc):
            raise
        (
            supabase.table("afp_bom_items")
            .update({"status": status})
            .eq("id", bom_item_id)
            .execute()
        )
