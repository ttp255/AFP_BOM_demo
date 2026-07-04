import unittest
from pathlib import Path

from fastapi import UploadFile

from app.routes.import_revit import read_revit_json
from app.services.import_service import import_revit_json


class ImportSchemaCompatibilityTest(unittest.IsolatedAsyncioTestCase):
    async def test_accepts_afp_test_case_schema_and_suggests_products(self):
        fixture = Path(r"D:\test_case_AFP\01_bathroom_wet_wall_waterproof.json")
        with fixture.open("rb") as stream:
            payload = await read_revit_json(UploadFile(filename=fixture.name, file=stream))

        result = import_revit_json(payload)

        self.assertEqual(result["status"], "imported")
        self.assertEqual(result["rooms_imported"], 1)
        self.assertEqual(result["surfaces_imported"], 2)
        self.assertEqual(result["bom_items_generated"], 2)
        self.assertGreater(result["suggestions_generated"], 0)
        self.assertNotIn("warnings", result)


if __name__ == "__main__":
    unittest.main()
