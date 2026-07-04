import json
import unittest
from unittest.mock import patch
import os

from app.services.import_service import import_revit_json
from app.db.supabase_client import supabase
from app.core.config import settings

class RevitImportFlowTest(unittest.TestCase):
    def test_import_and_suggestions_flow(self):
        # Ensure we use mock DB
        self.assertTrue(settings.AFP_USE_MOCK_DB, "This test requires AFP_USE_MOCK_DB to be True")
        
        # Read the file
        filepath = r"C:\Users\TAI\Downloads\paint_revit_export_test_10_files_FINAL\paint_revit_export_test_01.json"
        with open(filepath, "r", encoding="utf-8-sig") as f:
            payload = json.load(f)
            
        # Run import (which creates project, rooms, surfaces, bom items, suggestions)
        result = import_revit_json(payload)
        
        print("\n=== IMPORT RESULT ===")
        print(json.dumps(result, indent=2))
        
        # Verify result counters
        self.assertEqual(result["status"], "imported")
        self.assertEqual(result["rooms_imported"], 2) # Living Room, Master Bathroom
        self.assertEqual(result["surfaces_imported"], 5) # 2 room walls, 2 room ceilings, 1 exterior
        self.assertEqual(result["bom_items_generated"], 5)
        self.assertEqual(result["suggestions_generated"], 5)
        
        project_id = result["project_id"]
        
        # Query BOM items
        bom_items = supabase.table("afp_bom_items").select("*").eq("project_id", project_id).execute().data
        self.assertEqual(len(bom_items), 5)
        
        # Query suggestions
        suggestions = supabase.table("afp_bom_product_suggestions").select("*").execute().data
        project_suggestions = [s for s in suggestions if s["bom_item_id"] in [item["id"] for item in bom_items]]
        
        # We expect suggestions for each of the 5 BOM items
        # Let's map each suggestion to its corresponding product
        products = supabase.table("afp_products").select("*").execute().data
        prod_map = {p["id"]: p for p in products}
        
        # Print diagnostic suggestions
        print("\n=== SUGGESTION REPORT ===")
        for s in sorted(project_suggestions, key=lambda x: (x["bom_item_id"], x["rank_no"])):
            bom = next(item for item in bom_items if item["id"] == s["bom_item_id"])
            prod = prod_map.get(s["product_id"])
            print(
                f"BOM: {bom['item_name']} (Surface: {bom['surface']}, Finish: {bom['finish_type']}) -> "
                f"Rank {s['rank_no']}: {prod['product_name']} ({prod['sku']}) "
                f"Score: {s['final_score']} (Price: {s['price_score']}, Feature: {s['feature_score']}) "
                f"Qty: {s['estimated_required_package_qty']} packages, Cost: {s['estimated_total_cost']:,} {s['currency']}"
            )
            print(f"  Note: {s['note']}")
            
        # Assertions on match expectations
        # 1. Master Bathroom wall -> moisture-resistant interior wall paint -> HydroShield Bathroom Paint (AFP-WP-001)
        bath_wall_bom = next(b for b in bom_items if b["surface"] == "wall" and b["room_id"] in [
            r["id"] for r in supabase.table("afp_rooms").select("*").eq("room_name", "Master Bathroom").execute().data
        ])
        bath_wall_sugs = [s for s in project_suggestions if s["bom_item_id"] == bath_wall_bom["id"]]
        self.assertTrue(len(bath_wall_sugs) > 0)
        best_bath_wall_sug = next(s for s in bath_wall_sugs if s["is_best_option"])
        best_bath_wall_prod = prod_map[best_bath_wall_sug["product_id"]]
        self.assertEqual(best_bath_wall_prod["sku"], "AFP-WP-001")
        self.assertEqual(best_bath_wall_prod["product_type"], "interior_wall_paint")
        
        # 2. Living Room wall -> Rule rule_interior_wall_default -> interior_wall_paint -> CleanWall Interior Satin (AFP-IW-101)
        lr_wall_bom = next(b for b in bom_items if b["surface"] == "wall" and b["room_id"] in [
            r["id"] for r in supabase.table("afp_rooms").select("*").eq("room_name", "Living Room").execute().data
        ])
        lr_wall_sugs = [s for s in project_suggestions if s["bom_item_id"] == lr_wall_bom["id"]]
        self.assertTrue(len(lr_wall_sugs) > 0)
        best_lr_wall_sug = next(s for s in lr_wall_sugs if s["is_best_option"])
        best_lr_wall_prod = prod_map[best_lr_wall_sug["product_id"]]
        self.assertEqual(best_lr_wall_prod["sku"], "AFP-IW-101")
        
        # 3. Exterior -> Rule rule_exterior_facade -> exterior_wall_paint -> WeatherPro Exterior (AFP-EX-501)
        ext_bom = next(b for b in bom_items if b["surface"] == "exterior")
        ext_sugs = [s for s in project_suggestions if s["bom_item_id"] == ext_bom["id"]]
        self.assertTrue(len(ext_sugs) > 0)
        best_ext_sug = next(s for s in ext_sugs if s["is_best_option"])
        best_ext_prod = prod_map[best_ext_sug["product_id"]]
        self.assertEqual(best_ext_prod["sku"], "AFP-EX-501")

if __name__ == "__main__":
    unittest.main()

