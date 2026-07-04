from fastapi import APIRouter, HTTPException, Query, Response

from app.db.supabase_client import supabase
from app.services.export_service import create_export

router = APIRouter()


@router.get("/projects/{project_id}")
def list_exports(project_id: str):
    rows = (
        supabase.table("afp_bom_exports")
        .select("*")
        .eq("project_id", project_id)
        .execute()
        .data
        or []
    )
    # Keep the project boundary explicit at the response layer too. The database
    # query is scoped above, while this guard prevents another project's export
    # metadata from leaking if a database adapter ever returns extra rows.
    return [
        row
        for row in rows
        if str(row.get("project_id")) == str(project_id)
    ]


@router.post("/projects/{project_id}/{export_type}")
def export_project(
    project_id: str,
    export_type: str,
    scope: str = Query("approved_only", pattern="^(approved_only|all_items)$"),
):
    if export_type not in {"excel", "pdf", "json"}:
        raise HTTPException(status_code=400, detail="Export type must be excel, pdf, or json")
    try:
        metadata, content, media_type = create_export(project_id, export_type, scope)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{metadata["file_name"]}"',
            "X-Export-Id": str(metadata["id"]),
            "Access-Control-Expose-Headers": "Content-Disposition, X-Export-Id",
        },
    )
