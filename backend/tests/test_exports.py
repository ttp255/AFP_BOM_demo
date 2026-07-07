import unittest
from unittest.mock import patch

from app.db.mock_db import MockSupabase
from app.routes import exports
from app.services import export_service


class _Result:
    data = [
        {"id": "export-a", "project_id": "project-a", "file_name": "a.xlsx"},
        {"id": "export-b", "project_id": "project-b", "file_name": "b.xlsx"},
    ]


class _Table:
    def select(self, _columns):
        return self

    def eq(self, _column, _value):
        return self

    def execute(self):
        return _Result()


class _Database:
    def table(self, _name):
        return _Table()


class ExportRouteTests(unittest.TestCase):
    def test_list_exports_never_returns_another_projects_files(self):
        with patch.object(exports, "supabase", _Database()):
            result = exports.list_exports("project-a")

        self.assertEqual(
            result,
            [{"id": "export-a", "project_id": "project-a", "file_name": "a.xlsx"}],
        )

    def test_approved_only_export_requires_an_approved_suggestion(self):
        with patch.object(export_service, "_export_rows", return_value=[]):
            with self.assertRaisesRegex(ValueError, "Approve at least one"):
                export_service.create_export("project-a", "json", "approved_only")

    def test_export_rows_use_names_unit_price_and_total_price(self):
        db = MockSupabase()
        project_id = "project-a"
        bom = db.insert("afp_bom_items", {
            "project_id": project_id,
            "bom_code": "BOM-001",
            "material_name": "Interior paint",
            "quantity": 20,
        })
        product = db.rows["afp_products"][0]
        offer = db.rows["afp_product_suppliers"][0]
        supplier = db.rows["afp_suppliers"][0]
        db.insert("afp_bom_product_suggestions", {
            "bom_item_id": bom["id"],
            "product_id": product["id"],
            "supplier_id": supplier["id"],
            "product_supplier_id": offer["id"],
            "rank_no": 1,
            "suggestion_status": "approved",
            "estimated_required_package_qty": 3,
        })

        with patch.object(export_service, "supabase", db):
            rows = export_service._export_rows(project_id, "approved_only")

        self.assertEqual(rows[0]["product"], product["product_name"])
        self.assertEqual(rows[0]["supplier"], supplier["supplier_name"])
        self.assertEqual(rows[0]["unit_price"], offer["unit_price"])
        self.assertEqual(rows[0]["total_price"], 3 * offer["unit_price"])

    def test_json_export_includes_grand_total_price(self):
        rows = [{"total_price": 1200, "currency": "VND"}, {"total_price": 800, "currency": "VND"}]
        with patch.object(export_service, "_export_rows", return_value=rows):
            with patch.object(export_service, "supabase", MockSupabase()):
                _metadata, content, _media_type = export_service.create_export("project-a", "json", "approved_only")

        self.assertIn(b'"grand_total_price": 2000.0', content)

if __name__ == "__main__":
    unittest.main()