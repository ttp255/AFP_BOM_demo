import uuid

from postgrest.exceptions import APIError

from app.db.supabase_client import supabase
from app.services.bom_service import generate_paint_bom
from app.services.pipeline_service import suggest_products_for_project


def import_revit_json(payload: dict, project_id: str | None = None):
    project = payload["project"]

    if project_id is None:
        project_code = "PRJ-" + uuid.uuid4().hex[:8].upper()
        project_id = create_project(project, project_code)
    else:
        existing = (
            supabase.table("afp_projects")
            .select("*")
            .eq("id", project_id)
            .single()
            .execute()
            .data
        )
        if not existing:
            raise ValueError(f"Project {project_id} was not found")
        project_code = existing["project_code"]
        clear_project_import_data(project_id)
        update_project(project_id, project)

    room_count = 0
    surface_count = 0
    for room in payload.get("rooms", []):
        surface_count += import_room(project_id, room)
        room_count += 1

    if payload.get("exterior"):
        import_exterior(project_id, payload["exterior"])
        surface_count += 1

    bom_items = generate_paint_bom(project_id)
    warnings = []
    try:
        # Keep upload fast: hard filters and deterministic scoring are sufficient here;
        # external vector/LLM enrichment belongs outside the critical path.
        suggestions = suggest_products_for_project(project_id, enrich_with_ai=False)
    except Exception:
        suggestions = []
        warnings.append(
            "BOM imported successfully, but product suggestions could not be generated. "
            "Retry from the Product Suggestions page."
        )

    result = {
        "project_id": project_id,
        "project_code": project_code,
        "status": "imported",
        "rooms_imported": room_count,
        "surfaces_imported": surface_count,
        "bom_items_generated": len(bom_items),
        "suggestions_generated": len(suggestions),
    }
    if warnings:
        result["warnings"] = warnings
    return result


def create_project(project: dict, project_code: str) -> str:
    project_row = build_project_row(project, project_code)
    project_result = supabase.table("afp_projects").insert(project_row).execute()
    return project_result.data[0]["id"]


def update_project(project_id: str, project: dict) -> None:
    project_row = build_project_row(project)
    supabase.table("afp_projects").update(project_row).eq("id", project_id).execute()


def build_project_row(project: dict, project_code: str | None = None) -> dict:
    row = {
        "project_name": first_present(project, {}, "name", "project_name"),
        "revit_file_name": first_present(project, {}, "revit_file", "revit_file_name"),
        "location": project.get("location"),
        "status": "imported",
    }
    if project_code is not None:
        row["project_code"] = project_code
    return row


def clear_project_import_data(project_id: str) -> None:
    bom_items = (
        supabase.table("afp_bom_items")
        .select("*")
        .eq("project_id", project_id)
        .execute()
        .data
    )
    for item in bom_items:
        supabase.table("afp_bom_product_suggestions").delete().eq("bom_item_id", item["id"]).execute()

    supabase.table("afp_bom_items").delete().eq("project_id", project_id).execute()
    supabase.table("afp_revit_elements").delete().eq("project_id", project_id).execute()
    supabase.table("afp_rooms").delete().eq("project_id", project_id).execute()


def import_room(project_id: str, room: dict) -> int:
    room_name = first_present(room, {}, "name", "room_name")
    if not room_name:
        raise KeyError("rooms[].name or rooms[].room_name")
    room_row = {
        "project_id": project_id,
        "revit_room_id": first_present(room, {}, "revit_id", "room_code"),
        "room_number": first_present(room, {}, "number", "room_code"),
        "room_name": room_name,
        "room_type": first_present(
            room, {}, "room_type", default=detect_room_type(room_name)
        ),
        "area_m2": room.get("area_m2"),
        "perimeter_m": room.get("perimeter_m"),
        "height_m": room.get("height_m"),
    }

    result = supabase.table("afp_rooms").insert(room_row).execute()
    room_id = result.data[0]["id"]

    surface_count = 0
    surfaces = room.get("surfaces") or {}
    if isinstance(surfaces, list):
        surface_entries = (
            (surface.get("surface") or surface.get("surface_type"), surface)
            for surface in surfaces
            if isinstance(surface, dict)
        )
    elif isinstance(surfaces, dict):
        surface_entries = surfaces.items()
    else:
        raise ValueError("Room surfaces must be a JSON object or array")

    for surface_name, surface in surface_entries:
        if not surface_name:
            raise KeyError("rooms[].surfaces[].surface")
        import_surface(project_id, room_id, room, surface_name, surface)
        surface_count += 1
    return surface_count


def import_surface(project_id: str, room_id: str, room: dict, surface_name: str, surface: dict) -> None:
    normalized_surface = normalize_surface_name(surface_name)
    room_requirements = room.get("requirements") or {}
    finish_type = first_present(
        surface,
        room_requirements,
        "finish_type",
        "finish",
        default="interior_paint",
    )
    finish_type = normalize_enum_value(finish_type)
    substrate = normalize_enum_value(first_present(surface, room_requirements, "substrate"))
    condition = normalize_enum_value(
        first_present(surface, room_requirements, "condition", "current_condition", default="new")
    )
    gross_area = number_from(surface, "area_m2", "gross_area_m2", "net_area_m2", "area", default=0)
    opening_area = number_from(surface, "opening_area_m2", "opening_area", default=0)
    net_area = max(gross_area - opening_area, 0)

    row = {
        "project_id": project_id,
        "room_id": room_id,
        "revit_element_id": (
            surface.get("surface_id")
            or f"{first_present(room, {}, 'revit_id', 'room_code', default=room_id)}-{normalized_surface}"
        ),
        "surface": normalized_surface,
        "material_name": finish_type,
        "substrate": substrate,
        "condition": condition,
        "finish_type": finish_type,
        "gross_area_m2": gross_area,
        "opening_area_m2": opening_area,
        "net_area_m2": net_area,
        "source_payload": {"surface": surface, "requirements": room_requirements},
    }

    insert_revit_element(row)


def import_exterior(project_id: str, exterior: dict) -> None:
    gross_area = number_from(exterior, "facade_area_m2", "area_m2", "gross_area_m2", "area", default=0)
    requirements = exterior.get("requirements") or {}
    finish_type = normalize_enum_value(first_present(exterior, requirements, "finish_type", "finish", default="exterior_paint"))

    row = {
        "project_id": project_id,
        "room_id": None,
        "revit_element_id": "EXTERIOR-FACADE",
        "surface": "exterior",
        "material_name": finish_type,
        "substrate": normalize_enum_value(exterior.get("substrate")),
        "condition": normalize_enum_value(exterior.get("condition") or "new"),
        "finish_type": finish_type,
        "gross_area_m2": gross_area,
        "opening_area_m2": 0,
        "net_area_m2": gross_area,
        "source_payload": {"exterior": exterior, "requirements": requirements},
    }

    insert_revit_element(row)


def insert_revit_element(row: dict) -> None:
    """Insert into either the current schema or the older deployed AFP schema."""
    try:
        supabase.table("afp_revit_elements").insert(row).execute()
    except APIError as exc:
        if exc.code != "PGRST204":
            raise
        legacy_row = {
            "project_id": row["project_id"],
            "room_id": row.get("room_id"),
            "revit_element_id": row.get("revit_element_id"),
            "category": row.get("surface"),
            "material_name": row.get("material_name"),
            "area_m2": row.get("net_area_m2"),
            "raw_parameters": row.get("source_payload") or {},
        }
        supabase.table("afp_revit_elements").insert(legacy_row).execute()

def detect_room_type(room_name: str) -> str:
    name = room_name.lower()
    if "bath" in name or "toilet" in name or "wc" in name:
        return "Bathroom"
    if "kitchen" in name:
        return "Kitchen"
    if "bed" in name:
        return "Bedroom"
    if "living" in name:
        return "Living Room"
    return "Any"


def normalize_surface_name(surface_name: str) -> str:
    value = str(surface_name or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "walls": "wall",
        "interior_wall": "wall",
        "interior_walls": "wall",
        "ceilings": "ceiling",
        "feature_walls": "feature_wall",
    }
    return aliases.get(value, value)


def normalize_enum_value(value):
    if value in (None, ""):
        return value
    return str(value).strip().lower().replace("-", "_").replace(" ", "_")


def first_present(primary: dict, fallback: dict, *keys: str, default=None):
    for source in (primary, fallback):
        for key in keys:
            value = source.get(key)
            if value not in (None, ""):
                return value
    return default


def number_from(source: dict, *keys: str, default: float = 0) -> float:
    for key in keys:
        value = source.get(key)
        if value in (None, ""):
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return default
