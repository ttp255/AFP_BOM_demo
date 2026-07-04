from fastapi import APIRouter

from app.db.supabase_client import supabase
from app.services.bom_service import generate_paint_bom

router = APIRouter()


@router.get("/projects/{project_id}")
def list_bom_items(project_id: str):
    return supabase.table("afp_bom_items").select("*").eq("project_id", project_id).execute().data


@router.post("/projects/{project_id}/generate")
def generate_bom(project_id: str):
    items = generate_paint_bom(project_id)
    return {"project_id": project_id, "created_items": len(items), "items": items}

