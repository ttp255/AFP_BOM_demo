import unittest
from unittest.mock import patch

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

if __name__ == "__main__":
    unittest.main()