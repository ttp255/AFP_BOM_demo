"""Derive catalog requirements directly from imported BIM/BOM context."""

from app.db.supabase_client import supabase


def build_requirement_for_bom_item(bom_item: dict) -> dict:
    surface = normalize_value(bom_item.get("surface"))
    room_type = _room_type(bom_item)
    source_requirements = _source_requirements(bom_item)

    if room_type == "bathroom" and surface == "wall":
        return _requirement(
            "interior_wall_paint", "wet_area_wall",
            ["wet_area_wall", "bathroom_wall", "humidity_resistance"],
            ["moisture_resistant"],
            ["mold_resistant", "easy_clean", "low_odor", "waterproof"],
            1.15, "Bathroom wall needs a moisture-resistant interior wall coating.",
        )
    if surface in {"exterior", "exterior_wall", "facade"}:
        if source_requirements.get("salt_air_resistance") is True:
            return _requirement(
                "coastal_exterior_wall_paint", "exterior_facade",
                ["exterior_facade", "salt_air_exposure", "weather_exposed_wall"],
                ["salt_air_resistant", "weather_resistant", "uv_resistant"],
                ["mold_resistant", "color_retention"], 1.15,
                "Coastal facade needs salt-air, weather, and UV resistance.",
            )
        return _requirement(
            "exterior_wall_paint", "exterior_wall",
            ["exterior_wall", "exterior_facade", "weather_resistance", "uv_resistance"],
            ["uv_resistant"], ["water_resistant", "waterproof", "color_retention"],
            1.15, "Exterior facade needs weather and UV resistance.",
        )
    if surface == "ceiling":
        requirement = _requirement(
            "general_interior_wall_paint", "ceiling", ["ceiling", "interior_ceiling"], [],
            ["matte", "low_splash", "low_odor"], 1.10,
            "Interior ceiling needs a compatible low-splash matte coating.",
        )
        requirement["accepted_product_types"] = [
            "general_interior_wall_paint", "ceiling_paint", "interior_wall_paint",
        ]
        return requirement
    if surface == "feature_wall" or normalize_value(bom_item.get("finish_type")) == "decorative_paint":
        requirement = _requirement(
            "decorative_plaster_finish", "decorative_feature_wall",
            ["decorative_feature_wall", "feature_wall", "decorative_wall"],
            [], ["premium_finish", "decorative_effect", "feature_wall_effect"],
            1.10, "Feature wall needs a compatible decorative interior coating.",
        )
        requirement["accepted_product_types"] = [
            "decorative_plaster_finish", "decorative_shimmer_stone_finish",
            "decorative_copper_effect_paint", "decorative_metallic_paint",
            "decorative_bronze_effect_paint", "decorative_texture_effect_paint",
            "decorative_patina_effect_paint", "decorative_effect_primer",
            "premium_decorative_paint", "decorative_wall_paint",
        ]
        return requirement

    preferred = (
        ["washable", "easy_clean", "stain_resistant", "low_odor"]
        if room_type == "kitchen"
        else ["easy_clean", "washable", "low_voc", "low_odor"]
    )
    return _requirement(
        "interior_wall_paint", "interior_wall",
        ["interior_wall", "dry_interior_wall"], [], preferred,
        1.10, "Dry interior wall needs a low-odor interior coating.",
    )


def _room_type(bom_item: dict) -> str:
    if not bom_item.get("room_id"):
        return "exterior" if normalize_value(bom_item.get("surface")) == "exterior" else ""
    room = (
        supabase.table("afp_rooms").select("*").eq("id", bom_item["room_id"])
        .single().execute().data
    )
    return normalize_value((room or {}).get("room_type"))


def _source_requirements(bom_item: dict) -> dict:
    """Recover design requirements retained on the source Revit element."""
    element_id = bom_item.get("revit_element_id")
    if not element_id:
        source_ids = bom_item.get("source_element_ids") or []
        element_id = source_ids[0] if source_ids else None
    if not element_id:
        return {}
    element = (
        supabase.table("afp_revit_elements").select("*").eq("id", element_id)
        .single().execute().data
    ) or {}
    payload = element.get("source_payload") or element.get("raw_parameters") or {}
    return payload.get("requirements") or {}


def _requirement(product_type, usage_area, tags, required, preferred, waste_factor, description):
    return {
        "required_product_type": product_type,
        "usage_area": usage_area,
        "required_tags": tags,
        "required_features": required,
        "preferred_features": preferred,
        "waste_factor": waste_factor,
        # Catalog coverage is m2/L per coat. AFP finish systems require two coats.
        "required_coats": 2,
        "description": description,
    }


def normalize_value(value) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


