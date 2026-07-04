import math
from decimal import Decimal, InvalidOperation, ROUND_CEILING

from app.db.supabase_client import supabase


def rank_products_for_bom_item(bom_item: dict, products: list[dict], requirement: dict) -> list[dict]:
    ranked = []
    for product in products:
        supplier_rows = (
            supabase.table("afp_product_suppliers")
            .select("*, afp_suppliers(*)")
            .eq("product_id", product["id"])
            .eq("is_available", True)
            .execute()
            .data
        )
        for supplier_row in supplier_rows:
            supplier = supplier_row.get("afp_suppliers") or {}
            if supplier.get("is_active") is False:
                continue
            
            # 1. BOM item area
            bom_item_area = bom_item["quantity"]
            
            # 2. Get product coverage data
            coverage_m2_per_liter = product.get("coverage_m2_per_liter")
            package_size = product.get("package_size")
            package_area_m2 = product.get("package_area_m2")
            recommended_coats = product.get("recommended_coats") or requirement.get("required_coats", 2)
            
            # 3. Get supplier price data
            unit_price = supplier_row.get("unit_price")
            min_order_qty = supplier_row.get("min_order_qty")
            
            # 4. Calculate required painted area (BOM Area * Coats)
            required_painted_area = float(bom_item_area) * max(1, math.ceil(float(recommended_coats or 1)))
            
            # 5. Calculate package quantity
            package_qty = calculate_package_qty(
                required_painted_area,
                coverage_m2_per_liter,
                package_size,
                required_coats=None,  # Already multiplied
                min_order_qty=min_order_qty,
                package_area_m2=package_area_m2,
            )
            
            # 6. Calculate total cost
            total_cost = None
            if unit_price is not None:
                total_cost = package_qty * float(unit_price)
                
            score = calculate_score(product, supplier_row, requirement, package_qty)
            ranked.append({
                "product": product,
                "supplier_row": supplier_row,
                "score": score,
                "required_painted_area": required_painted_area,
                "package_qty": package_qty,
                "total_cost": total_cost,
            })
    known_costs = [item["total_cost"] for item in ranked if item["total_cost"] is not None]
    lowest_cost = min(known_costs) if known_costs else None
    for item in ranked:
        total_cost = item["total_cost"]
        item["score"]["price_score"] = (
            round(lowest_cost / total_cost * 100, 2)
            if lowest_cost is not None and total_cost else 35
        )
        item["score"]["final_score"] = calculate_final_score(item["score"])
    ranked.sort(key=lambda item: item["score"]["final_score"], reverse=True)

    # Product rank is the user-facing decision. Keep only its best supplier offer.
    best_offer_by_product = {}
    for item in ranked:
        product_id = item["product"]["id"]
        if product_id not in best_offer_by_product:
            best_offer_by_product[product_id] = item
    return list(best_offer_by_product.values())


def calculate_package_qty(
    required_area_m2,
    coverage_m2_per_liter,
    package_size,
    required_coats=None,
    min_order_qty=1,
    package_area_m2=None,
) -> int:
    """Return whole packages needed for all coats, respecting supplier minimums."""
    minimum = max(1, _ceil_decimal(min_order_qty or 1))
    area = _decimal(required_area_m2)
    if area <= 0:
        return 0

    package_area = _decimal(package_area_m2)
    coverage = _decimal(coverage_m2_per_liter)
    size = _decimal(package_size)
    if package_area > 0:
        coverage_per_package = package_area
    elif coverage > 0 and size > 0:
        coverage_per_package = coverage * size
    else:
        return minimum

    if required_coats is not None:
        area *= max(1, _ceil_decimal(required_coats))

    calculated = _ceil_decimal(area / coverage_per_package)
    return max(minimum, calculated)


def _decimal(value) -> Decimal:
    """Convert catalog numbers without introducing binary float rounding."""
    if value is None:
        return Decimal(0)
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal(0)
    return result if result.is_finite() else Decimal(0)


def _ceil_decimal(value) -> int:
    return int(_decimal(value).to_integral_value(rounding=ROUND_CEILING))


def calculate_score(
    product: dict, supplier_row: dict, requirement: dict, package_qty: int = 1,
) -> dict:
    feature_score = score_features(product, requirement)
    semantic_score = (
        float(product["semantic_score"]) * 100
        if product.get("semantic_score") is not None else 0.0
    )
    price_score = 35
    stock_score = score_stock(supplier_row, package_qty)
    delivery_score = score_delivery(supplier_row)
    supplier_score = score_supplier(supplier_row)
    score = {

        "feature_score": feature_score,
        "semantic_score": round(semantic_score, 2),
        "price_score": price_score,
        "stock_score": stock_score,
        "delivery_score": delivery_score,
        "supplier_score": supplier_score,
    }
    score["final_score"] = calculate_final_score(score)
    return score


def calculate_final_score(score: dict) -> float:
    return round(
        score["semantic_score"] * 0.30
        + score["feature_score"] * 0.30
        + score["price_score"] * 0.15
        + score["stock_score"] * 0.15
        + score["delivery_score"] * 0.10,
        2,
    )


def score_features(product: dict, requirement: dict) -> float:
    features = set(product.get("features") or [])
    required = set(requirement.get("required_features") or [])
    preferred = set(requirement.get("preferred_features") or [])
    if required and not required.issubset(features):
        return 0
    required_score = 1 if not required else len(required & features) / len(required)
    preferred_score = 0 if not preferred else len(preferred & features) / len(preferred)
    return round((required_score * .75 + preferred_score * .25) * 100, 2)


def score_stock(supplier_row: dict, required_qty: int = 1) -> int:
    stock = supplier_row.get("stock_qty")
    if stock is None:
        return 50
    if stock <= 0:
        return 0
    if stock >= required_qty:
        return 100
    return 60


def score_delivery(supplier_row: dict) -> int:
    days = supplier_row.get("delivery_days")
    if days is None:
        return 50
    if days <= 2:
        return 100
    if days <= 5:
        return 80
    if days <= 10:
        return 50
    return 20


def score_supplier(supplier_row: dict) -> float:
    supplier = supplier_row.get("afp_suppliers") or {}
    rating = supplier.get("rating")
    return 60 if rating is None else min(max(float(rating) * 20, 0), 100)
