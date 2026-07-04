from fastapi import APIRouter, HTTPException, Response

from app.db.supabase_client import supabase

router = APIRouter()


@router.get("")
def list_projects():
    return supabase.table("afp_projects").select("*").order("created_at", desc=True).execute().data


@router.get("/{project_id}")
def get_project(project_id: str):
    return supabase.table("afp_projects").select("*").eq("id", project_id).single().execute().data


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: str):
    deleted = supabase.table("afp_projects").delete().eq("id", project_id).execute().data
    if not deleted:
        raise HTTPException(status_code=404, detail="Project not found")
    return Response(status_code=204)


@router.get("/{project_id}/rooms")
def list_rooms(project_id: str):
    return supabase.table("afp_rooms").select("*").eq("project_id", project_id).execute().data


@router.get("/{project_id}/elements")
def list_elements(project_id: str):
    return supabase.table("afp_revit_elements").select("*").eq("project_id", project_id).execute().data

