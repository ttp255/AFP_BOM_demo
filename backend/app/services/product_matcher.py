from app.db.supabase_client import supabase


def structured_semantic_score(product: dict, requirement: dict) -> float:
    """Return deterministic 0..1 relevance when vector evidence is absent."""
    required_type = requirement.get("required_product_type")
    accepted_types = set(requirement.get("accepted_product_types") or [])
    if required_type:
        accepted_types.add(required_type)
    type_score = 1.0 if product.get("product_type") in accepted_types else 0.0

    product_usage = set(product.get("usage_areas") or [])
    product_usage.update(product.get("recommended_for_tags") or [])
    product_usage.update(product.get("room_suitability") or [])
    wanted_usage = set(requirement.get("required_tags") or [])
    if requirement.get("usage_area"):
        wanted_usage.add(requirement["usage_area"])
    usage_score = len(product_usage & wanted_usage) / len(wanted_usage) if wanted_usage else 1.0

    features = set(product.get("features") or [])
    required = set(requirement.get("required_features") or [])
    preferred = set(requirement.get("preferred_features") or [])
    required_score = len(features & required) / len(required) if required else 1.0
    preferred_score = len(features & preferred) / len(preferred) if preferred else 1.0

    return round(type_score * 0.35 + usage_score * 0.25 + required_score * 0.25 + preferred_score * 0.15, 4)


def filter_products(
    requirement: dict, semantic_scores: dict[str, float] | None = None,
) -> list[dict]:
    products = (
        supabase.table("afp_products").select("*").eq("status", "active")
        .execute().data
    )
    type_aliases = {
        "coastal_exterior_wall_paint": [
            "coastal_exterior_wall_paint", "exterior_wall_paint",
        ],
    }
    accepted_types = requirement.get("accepted_product_types") or type_aliases.get(
        requirement["required_product_type"], [requirement["required_product_type"]]
    )
    products = [
        product for product in products
        if product.get("product_type") in accepted_types
    ]

    valid = []
    for product in products:
        if not supports_usage(product, requirement):
            continue
        features = set(product.get("features") or [])
        required = requirement.get("required_features") or []
        if not set(required).issubset(features):
            continue
        required_tags = set(requirement.get("required_tags") or [])
        excluded_tags = set(product.get("not_recommended_for_tags") or [])
        if required_tags.intersection(excluded_tags):
            continue
        # Semantic retrieval is ranking evidence, not a hard candidate filter.
        vector_score = (semantic_scores or {}).get(product["id"])
        product = {
            **product,
            "semantic_score": vector_score if vector_score is not None else structured_semantic_score(product, requirement),
        }
        valid.append(product)
    return valid


def supports_usage(product: dict, requirement: dict) -> bool:
    usage_area = requirement["usage_area"]
    accepted = set(product.get("usage_areas") or [])
    accepted.update(product.get("recommended_for_tags") or [])
    accepted.update(product.get("room_suitability") or [])
    required_tags = set(requirement.get("required_tags") or [])
    if usage_area in accepted or required_tags.intersection(accepted):
        return True
    if usage_area == "exterior_facade" and "exterior_wall" in accepted:
        return True
    return (
        usage_area == "ceiling"
        and requirement.get("required_product_type") in {"wall_paint", "interior_wall_paint", "general_interior_wall_paint", "ceiling_paint"}
        and "interior_wall" in accepted
    )

