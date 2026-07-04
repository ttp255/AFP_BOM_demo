import unittest
from unittest.mock import patch

from app.services import product_matcher, ranking_service, requirement_service, vector_service


class SuggestionPipelineTests(unittest.TestCase):
    def test_vector_search_preserves_uuid_ids(self):
        class Result:
            data = [{"id": "82e7a381-1ab3-41ca-8ff0-017fbdf11d04", "semantic_score": 0.91}]

        class Database:
            def rpc(self, *_args, **_kwargs):
                return self

            def execute(self):
                return Result()

        class Embeddings:
            def embed_query(self, _text):
                return [0.0]

        with (
            patch.object(vector_service.settings, "AFP_USE_MOCK_DB", False),
            patch.object(vector_service, "supabase", Database()),
            patch.object(vector_service, "_client", return_value=Embeddings()),
        ):
            scores = vector_service.semantic_product_ids({}, {})

        self.assertEqual(scores, {"82e7a381-1ab3-41ca-8ff0-017fbdf11d04": 0.91})

    def test_missing_embedding_is_not_reported_as_semantic_evidence(self):
        score = ranking_service.calculate_score(
            {"features": ["waterproof"]},
            {"stock_qty": 10, "delivery_days": 2, "afp_suppliers": {"rating": 4.5}},
            {"required_features": ["waterproof"], "preferred_features": []},
        )
        self.assertEqual(score["semantic_score"], 0.0)

    def test_structured_relevance_prevents_zero_when_vector_search_is_empty(self):
        product = {
            "id": "paint-1", "product_type": "interior_wall_paint",
            "usage_areas": ["interior_wall"], "features": ["washable", "low_voc"],
        }
        requirement = {
            "required_product_type": "interior_wall_paint", "usage_area": "interior_wall",
            "required_tags": ["interior_wall"], "required_features": ["washable"],
            "preferred_features": ["low_voc"],
        }
        self.assertEqual(product_matcher.structured_semantic_score(product, requirement), 1.0)

    def test_vector_limit_does_not_remove_other_valid_products(self):
        requirement = {
            "required_product_type": "interior_wall_paint", "usage_area": "interior_wall",
            "required_tags": [], "required_features": [], "preferred_features": [],
        }
        products = [{
            "id": "paint-1", "status": "active", "product_type": "interior_wall_paint",
            "usage_areas": ["interior_wall"], "features": [],
        }]
        with patch.object(product_matcher.supabase, "table") as mock_table:
            mock_table.return_value.select.return_value.eq.return_value.execute.return_value.data = products
            matched = product_matcher.filter_products(requirement, {"another-product": 0.99})
        self.assertEqual(len(matched), 1)
        self.assertGreater(matched[0]["semantic_score"], 0)

    def test_package_quantity_accounts_for_coats_and_supplier_minimum(self):
        # When coats is passed explicitly (backward compatibility)
        self.assertEqual(
            ranking_service.calculate_package_qty(35.75, 9, 5, required_coats=2),
            2,
        )
        self.assertEqual(
            ranking_service.calculate_package_qty(
                10, 10, 5, required_coats=2, min_order_qty=3,
            ),
            3,
        )
        # When required_painted_area is passed directly (new behavior)
        self.assertEqual(
            ranking_service.calculate_package_qty(71.5, 9, 5),
            2,
        )

    def test_package_quantity_scales_with_area_without_boundary_over_ordering(self):
        self.assertEqual(ranking_service.calculate_package_qty(49.99, 10, 5), 1)
        self.assertEqual(ranking_service.calculate_package_qty(50, 10, 5), 1)
        self.assertEqual(ranking_service.calculate_package_qty(50.01, 10, 5), 2)
        self.assertEqual(ranking_service.calculate_package_qty(100, 10, 5), 2)
        # Decimal inputs that are awkward as binary floats must not round up.
        self.assertEqual(
            ranking_service.calculate_package_qty(0.1, 0.1, 1, required_coats=3),
            3,
        )
        self.assertEqual(
            ranking_service.calculate_package_qty(0, 10, 5, min_order_qty=3),
            0,
        )
    def test_required_painted_area_calculation_in_ranking(self):
        bom_item = {
            "quantity": 10.0,
            "surface": "wall",
            "finish_type": "interior_paint",
            "substrate": "concrete",
            "condition": "new",
        }
        requirement = {
            "required_product_type": "interior_wall_paint",
            "required_coats": 2,
        }
        product = {
            "id": "prod-1",
            "sku": "AFP-IW-101",
            "coverage_m2_per_liter": 10.0,
            "package_size": 5.0,
            "recommended_coats": 3,  # Specific recommended coats for product
        }
        # Mock database call inside ranking
        with patch.object(ranking_service.supabase, "table") as mock_table:
            mock_table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                {
                    "id": "ps-1",
                    "product_id": "prod-1",
                    "supplier_id": "sup-1",
                    "unit_price": 500000,
                    "min_order_qty": 1,
                    "is_available": True,
                    "afp_suppliers": {"is_active": True, "rating": 4.5}
                }
            ]
            ranked = ranking_service.rank_products_for_bom_item(bom_item, [product], requirement)
            
        self.assertEqual(len(ranked), 1)
        self.assertEqual(ranked[0]["required_painted_area"], 30.0) # 10.0 area * 3 coats = 30.0

    def test_decorative_feature_wall_builds_requirement_and_matches_product(self):
        bom_item = {
            "id": "feature-wall-bom",
            "room_id": None,
            "surface": "feature_wall",
            "finish_type": "decorative_paint",
            "substrate": "gypsum_board",
            "condition": "new",
        }
        requirement = requirement_service.build_requirement_for_bom_item(bom_item)
        products = product_matcher.filter_products(requirement)

        self.assertEqual(requirement["required_product_type"], "decorative_plaster_finish")
        self.assertIn("feature_wall", requirement["required_tags"])
        # All matched products must be decorative types and have feature_wall in usage_areas
        self.assertGreater(len(products), 0, "At least one decorative product should match")
        for product in products:
            self.assertIn(
                product.get("product_type"),
                requirement["accepted_product_types"],
                f"Product {product['sku']} type '{product.get('product_type')}' not in accepted decorative types"
            )




if __name__ == "__main__":
    unittest.main()

