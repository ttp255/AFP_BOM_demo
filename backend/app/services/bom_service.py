from postgrest.exceptions import APIError

from app.db.supabase_client import supabase


def generate_paint_bom(project_id: str):
    existing = (
        supabase.table("afp_bom_items")
        .select("*")
        .eq("project_id", project_id)
        .execute()
        .data
    )
    if existing:
        for item in existing:
            supabase.table("afp_bom_product_suggestions").delete().eq("bom_item_id", item["id"]).execute()
        supabase.table("afp_bom_items").delete().eq("project_id", project_id).execute()

    elements = (
        supabase.table("afp_revit_elements")
        .select("*")
        .eq("project_id", project_id)
        .execute()
        .data
    )

    items = []
    for index, element in enumerate(elements, start=1):
        waste_factor = 1.10
        net_area = float(element.get("net_area_m2") or element.get("area_m2") or 0)
        surface = element.get("surface") or element.get("category")
        quantity = round(net_area * waste_factor, 2)
        row = {
            "project_id": project_id,
            "room_id": element.get("room_id"),
            "revit_element_id": element["id"],
            "bom_code": f"BOM-{project_id}-{index:04d}",
            "item_name": build_item_name(element),
            "category": "Paint",
            "surface": surface,
            "material_name": element.get("material_name"),
            "finish_type": element.get("finish_type"),
            "substrate": element.get("substrate"),
            "condition": element.get("condition"),
            "quantity": quantity,
            "unit": "m2",
            "gross_area_m2": element.get("gross_area_m2"),
            "opening_area_m2": element.get("opening_area_m2"),
            "net_area_m2": net_area,
            "waste_factor": waste_factor,
            "formula_type": "paint_area",
            "formula_note": "quantity = area_m2 x waste_factor",
            "requirement_status": "pending",
            "suggestion_status": "pending",
        }
        result = insert_bom_item(row, element)
        items.append(result.data[0])
    return items


def insert_bom_item(row: dict, element: dict):
    """Insert into either the current schema or the older derloyed AFP schema."""
    try:
        return supabase.table("afp_bom_items").insert(row).execute()
    except APIError as exc:
        if exc.code != "PGRST204":
            raise
        legacy_row = {
            "project_id": row["project_id"],
            "room_id": row.get("room_id"),
            "source_element_ids": [element["id"]],
            "item_name": row["item_name"],
            "category": row["category"],
            "surface": row.get("surface"),
            "raw_material_name": row.get("material_name"),
            "quantity": row["quantity"],
            "unit": row["unit"],
            "waste_factor": row["waste_factor"],
            "formula_type": row["formula_type"],
            "formula_note": row["formula_note"],
            "status": "pending",
            "suggestion_status": "pending",
        }
        return supabase.table("afp_bom_items").insert(legacy_row).execute()

def build_item_name(element: dict) -> str:
    surface = element.get("surface") or element.get("category")
    if surface == "ceiling":
        return "Ceiling paint"
    if surface == "exterior":
        return "Exterior facade paint"
    if surface == "feature_wall":
        return "Decorative feature wall paint"
    return "Interior wall paint"

