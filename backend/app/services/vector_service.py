"""NVIDIA embeddings + Supabase pgvector retrieval for catalog products."""

from __future__ import annotations

from app.core.config import settings
from app.db.supabase_client import supabase


def _join(value) -> str:
    """Render a scalar or list as a comma-separated string."""
    if isinstance(value, list):
        return ", ".join(str(v) for v in value if v)
    return str(value) if value not in (None, "") else ""


def product_embedding_text(product: dict) -> str:
    """Build a rich natural-language passage for the product embedding.

    Uses prose sentences (not key:value pairs) so that the NV-EmbedQA
    passage vector occupies the same semantic space as a natural-language
    query vector, maximising cosine similarity.
    """
    name = product.get("product_name") or ""
    brand = product.get("brand") or ""
    category = product.get("raw_category") or ""
    p_type = product.get("product_type") or ""
    usage = _join(product.get("usage_areas") or [])
    features = _join(product.get("features") or [])
    rooms = _join(product.get("room_suitability") or [])
    surfaces = _join(product.get("surface_types") or [])
    rec_tags = _join(product.get("recommended_for_tags") or [])
    not_tags = _join(product.get("not_recommended_for_tags") or [])
    func_desc = product.get("function_description") or ""
    eff_reason = product.get("effective_reason") or ""

    parts: list[str] = []
    if name:
        header = name
        if brand:
            header += f" by {brand}"
        if category:
            header += f" — {category}"
        parts.append(header + ".")
    if p_type:
        parts.append(f"This is a {p_type.replace('_', ' ')}.")
    if usage:
        parts.append(f"Suitable for use in: {usage}.")
    if surfaces:
        parts.append(f"Designed for surface types: {surfaces}.")
    if rooms:
        parts.append(f"Recommended for rooms: {rooms}.")
    if features:
        parts.append(f"Key features include: {features}.")
    if rec_tags:
        parts.append(f"Best applied to: {rec_tags}.")
    if not_tags:
        parts.append(f"Not recommended for: {not_tags}.")
    if func_desc:
        parts.append(func_desc)
    if eff_reason:
        parts.append(eff_reason)
    return " ".join(parts)


# Surface-type vocabulary that maps to human-readable phrases used in product
# embedding texts, so that the query vector lands near the right product vectors.
_SURFACE_LABELS: dict[str, str] = {
    "ceiling": "interior ceiling",
    "wall": "interior wall",
    "exterior": "exterior facade",
    "exterior_wall": "exterior facade wall",
    "facade": "exterior facade",
    "bathroom_wall": "bathroom wet area wall",
    "wet_area_wall": "wet area wall with high humidity",
    "feature_wall": "decorative feature wall",
    "metal": "metal surface",
    "floor": "floor surface",
}


def requirement_embedding_text(requirement: dict, bom_item: dict) -> str:
    """Build a natural-language query sentence for NV-EmbedQA (input_type=query).

    The text should read like a human describing what coating they need for a
    surface, so that the query vector is close to the matching product passage
    vectors in embedding space.
    """
    surface_raw = str(bom_item.get("surface") or "").strip().lower()
    surface_label = _SURFACE_LABELS.get(surface_raw, surface_raw.replace("_", " "))

    item_name = bom_item.get("item_name") or ""
    room_type = str(bom_item.get("room_type") or "").replace("_", " ")
    material = bom_item.get("material_name") or ""
    substrate = bom_item.get("substrate") or ""
    condition = bom_item.get("condition") or ""
    finish = str(bom_item.get("finish_type") or "").replace("_", " ")

    p_type = str(requirement.get("required_product_type") or "").replace("_", " ")
    usage_area = str(requirement.get("usage_area") or "").replace("_", " ")
    req_features: list = requirement.get("required_features") or []
    pref_features: list = requirement.get("preferred_features") or []
    description = requirement.get("description") or ""

    # --- Compose natural-language sentences ---
    sentences: list[str] = []

    # Sentence 1: location + surface
    loc_parts = [p for p in [room_type, surface_label] if p]
    if item_name:
        sentences.append(f"This BOM item covers {item_name}.")
    if loc_parts:
        sentences.append(f"The surface is a {' '.join(loc_parts)}.")

    # Sentence 2: substrate / material / condition
    detail_parts = []
    if substrate:
        detail_parts.append(f"substrate is {substrate}")
    if material:
        detail_parts.append(f"material is {material}")
    if condition:
        detail_parts.append(f"condition is {condition}")
    if finish:
        detail_parts.append(f"finish type is {finish}")
    if detail_parts:
        sentences.append("The " + ", ".join(detail_parts) + ".")

    # Sentence 3: product type and usage area needed
    if p_type:
        sentences.append(f"A {p_type} is required for this surface.")
    if usage_area and usage_area != p_type:
        sentences.append(f"The intended usage area is {usage_area}.")

    # Sentence 4: required features
    if req_features:
        feat_str = ", ".join(str(f).replace("_", " ") for f in req_features)
        sentences.append(f"The coating must have the following properties: {feat_str}.")

    # Sentence 5: preferred features
    if pref_features:
        pref_str = ", ".join(str(f).replace("_", " ") for f in pref_features)
        sentences.append(f"Preferred additional properties include: {pref_str}.")

    # Sentence 6: human-readable description from the rule
    if description:
        sentences.append(description)

    return " ".join(sentences)


def _client():
    if not settings.NVIDIA_KEY:
        return None
    from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings
    return NVIDIAEmbeddings(
        model=settings.LLM_EMBEDDING_MODEL, api_key=settings.NVIDIA_KEY, timeout=60.0
    )


def index_products(products: list[dict] | None = None) -> int:
    """Embed active products after catalog imports or product changes."""
    client = _client()
    if client is None or settings.AFP_USE_MOCK_DB:
        return 0
    products = products or (
        supabase.table("afp_products").select("*").eq("status", "active").execute().data
    )
    texts = [product_embedding_text(product) for product in products]
    for product, text, vector in zip(products, texts, client.embed_documents(texts)):
        supabase.table("afp_products").update({
            "embedding_text": text, "embedding": vector,
        }).eq("id", product["id"]).execute()
    return len(products)


def semantic_product_ids(requirement: dict, bom_item: dict) -> dict[str | int, float]:
    """Return ID -> cosine similarity, falling back to deterministic ranking."""
    if settings.AFP_USE_MOCK_DB:
        return {}
    try:
        client = _client()
        if client is None:
            return {}
        vector = client.embed_query(requirement_embedding_text(requirement, bom_item))
        result = supabase.rpc("match_products_hybrid", {
            "query_embedding": vector,
            "match_product_type": requirement.get("required_product_type"),
            "match_tags": requirement.get("required_tags") or [requirement.get("usage_area")],
            "match_features": requirement.get("required_features") or [],
            "match_count": settings.VECTOR_MATCH_COUNT,
        }).execute()
        return {str(row["id"]): float(row["semantic_score"]) for row in (result.data or [])}
    except Exception:
        return {}
