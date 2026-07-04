from typing import Any

from fastapi import APIRouter, Query

from app.db.supabase_client import supabase

router = APIRouter()


def _matches(row: dict[str, Any], fields: tuple[str, ...], query: str) -> bool:
    values: list[str] = []
    for field in fields:
        value = row.get(field)
        if isinstance(value, list):
            values.extend(str(item) for item in value)
        elif value is not None:
            values.append(str(value))
    return query in " ".join(values).casefold()


@router.get("")
def global_search(q: str = Query(min_length=1, max_length=100), limit: int = Query(5, ge=1, le=10)):
    query = q.strip().casefold()
    if not query:
        return {"projects": [], "rooms": [], "products": []}

    projects = supabase.table("afp_projects").select("*").execute().data or []
    rooms = supabase.table("afp_rooms").select("*").execute().data or []
    products = supabase.table("afp_products").select("*").execute().data or []
    projects_by_id = {str(project["id"]): project for project in projects}

    project_results = [
        {
            "id": project["id"],
            "title": project.get("project_name") or "Untitled project",
            "subtitle": project.get("project_code") or project.get("location") or "Project",
            "href": f"/projects/{project['id']}",
        }
        for project in projects
        if _matches(project, ("project_name", "project_code", "location", "revit_file_name"), query)
    ][:limit]

    room_results = []
    for room in rooms:
        if not _matches(room, ("room_name", "room_number", "room_code", "level_name", "room_type"), query):
            continue
        project = projects_by_id.get(str(room.get("project_id")), {})
        room_results.append(
            {
                "id": room["id"],
                "title": room.get("room_name") or "Unnamed room",
                "subtitle": " · ".join(
                    str(part)
                    for part in (room.get("room_number"), room.get("level_name"), project.get("project_name"))
                    if part
                )
                or "Room",
                "href": f"/projects/{room['project_id']}/rooms?room={room['id']}",
            }
        )
        if len(room_results) == limit:
            break

    product_results = [
        {
            "id": product["id"],
            "title": product.get("product_name") or "Unnamed product",
            "subtitle": " · ".join(
                str(part) for part in (product.get("sku"), product.get("brand"), product.get("product_type")) if part
            )
            or "Product",
            "href": f"/products?q={product.get('sku') or product.get('product_name', '')}",
        }
        for product in products
        if _matches(
            product,
            ("product_name", "sku", "brand", "category", "product_type", "usage_areas", "features"),
            query,
        )
    ][:limit]

    return {"projects": project_results, "rooms": room_results, "products": product_results}
