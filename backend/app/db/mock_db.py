from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


TABLES = [
    "afp_projects",
    "afp_rooms",
    "afp_revit_elements",
    "afp_bom_items",
    "afp_products",
    "afp_suppliers",
    "afp_product_suppliers",
    "afp_bom_product_suggestions",
    "afp_bom_exports",
]


class MockResult:
    def __init__(self, data: Any):
        self.data = data


class MockTable:
    def __init__(self, db: "MockSupabase", name: str):
        self.db = db
        self.name = name
        self.filters: list[tuple[str, Any]] = []
        self.single_row = False
        self.select_spec = "*"
        self.pending_insert: dict[str, Any] | list[dict[str, Any]] | None = None
        self.pending_update: dict[str, Any] | None = None
        self.pending_delete = False
        self.order_by: tuple[str, bool] | None = None

    def select(self, spec: str = "*") -> "MockTable":
        self.select_spec = spec
        return self

    def eq(self, column: str, value: Any) -> "MockTable":
        self.filters.append((column, value))
        return self

    def single(self) -> "MockTable":
        self.single_row = True
        return self

    def order(self, column: str, desc: bool = False) -> "MockTable":
        self.order_by = (column, desc)
        return self

    def insert(self, rows: dict[str, Any] | list[dict[str, Any]]) -> "MockTable":
        self.pending_insert = rows
        return self

    def update(self, values: dict[str, Any]) -> "MockTable":
        self.pending_update = values
        return self

    def delete(self) -> "MockTable":
        self.pending_delete = True
        return self

    def execute(self) -> MockResult:
        if self.pending_insert is not None:
            rows = self.pending_insert if isinstance(self.pending_insert, list) else [self.pending_insert]
            created = [self.db.insert(self.name, row) for row in rows]
            return MockResult(created)

        if self.pending_update is not None:
            updated = self.db.update(self.name, self.filters, self.pending_update)
            return MockResult(updated[0] if self.single_row and updated else updated)

        if self.pending_delete:
            deleted = self.db.delete(self.name, self.filters)
            return MockResult(deleted[0] if self.single_row and deleted else deleted)

        rows = self.db.find(self.name, self.filters)
        if self.order_by:
            column, descending = self.order_by
            rows.sort(key=lambda row: row.get(column) or "", reverse=descending)
        if "afp_suppliers" in self.select_spec and self.name == "afp_product_suppliers":
            for row in rows:
                supplier = self.db.find("afp_suppliers", [("id", row.get("supplier_id"))])
                row["afp_suppliers"] = supplier[0] if supplier else None
        if self.single_row:
            return MockResult(rows[0] if rows else None)
        return MockResult(rows)


class MockSupabase:
    def __init__(self):
        self.rows: dict[str, list[dict[str, Any]]] = {table: [] for table in TABLES}
        self.seed()

    def table(self, name: str) -> MockTable:
        if name not in self.rows:
            self.rows[name] = []
        return MockTable(self, name)

    def insert(self, table: str, row: dict[str, Any]) -> dict[str, Any]:
        created = deepcopy(row)
        created["id"] = str(uuid4())
        self.rows[table].append(created)
        return deepcopy(created)

    def find(self, table: str, filters: list[tuple[str, Any]]) -> list[dict[str, Any]]:
        result = []
        for row in self.rows.get(table, []):
            if all(str(row.get(column)) == str(value) for column, value in filters):
                result.append(deepcopy(row))
        return result

    def update(self, table: str, filters: list[tuple[str, Any]], values: dict[str, Any]) -> list[dict[str, Any]]:
        updated = []
        for row in self.rows.get(table, []):
            if all(str(row.get(column)) == str(value) for column, value in filters):
                row.update(deepcopy(values))
                updated.append(deepcopy(row))
        return updated

    def delete(self, table: str, filters: list[tuple[str, Any]]) -> list[dict[str, Any]]:
        kept = []
        deleted = []
        for row in self.rows.get(table, []):
            if all(str(row.get(column)) == str(value) for column, value in filters):
                deleted.append(deepcopy(row))
            else:
                kept.append(row)
        self.rows[table] = kept
        if table == "afp_projects":
            for project in deleted:
                self._delete_project_children(project["id"] )
        return deleted

    def _delete_project_children(self, project_id: Any) -> None:
        bom_ids = {row["id"] for row in self.rows["afp_bom_items"] if str(row.get("project_id")) == str(project_id)}
        self.rows["afp_bom_product_suggestions"] = [row for row in self.rows["afp_bom_product_suggestions"] if row.get("bom_item_id") not in bom_ids]
        for table in ("afp_rooms", "afp_revit_elements", "afp_bom_items", "afp_bom_exports"):
            self.rows[table] = [row for row in self.rows[table] if str(row.get("project_id")) != str(project_id)]

    def seed(self) -> None:
        products = [
            ("AFP-WP-001", "HydroShield Bathroom Paint", "AFP Paint", "interior_wall_paint", ["wet_area_wall"], ["waterproof", "moisture_resistant", "mold_resistant"], ["wall"], 9, 5),
            ("AFP-IW-101", "CleanWall Interior Satin", "AFP Paint", "interior_wall_paint", ["interior_wall"], ["interior", "washable", "low_odor", "easy_clean"], ["wall"], 11, 5),
            ("AFP-EX-501", "WeatherPro Exterior", "AFP Paint", "exterior_wall_paint", ["exterior_wall"], ["weather_resistant", "uv_resistant", "waterproof", "salt_air_resistant"], ["exterior"], 8, 18),
            ("AFP-CL-201", "QuietMatte Ceiling", "AFP Paint", "wall_paint", ["ceiling"], ["matte", "low_splash", "low_odor"], ["ceiling"], 12, 5),
            ("AFP-DW-301", "ArtSmooth Feature Wall", "AFP Paint", "decorative_wall_paint", ["decorative_feature_wall"], ["interior", "decorative", "premium_smooth", "washable", "low_voc"], ["feature_wall"], 10, 5),
        ]
        for item in products:
            self.insert("afp_products", {
                "sku": item[0],
                "product_name": item[1],
                "brand": item[2],
                "raw_category": "Paint",
                "category": "Paint",
                "product_type": item[3],
                "usage_areas": item[4],
                "features": item[5],
                "surface_types": item[6],
                "finish_options": ["interior_paint", "exterior_paint"],
                "sheen": "matte",
                "coverage_m2_per_liter": item[7],
                "package_size": item[8],
                "package_unit": "L",
                "status": "active",
            })

        supplier = self.insert("afp_suppliers", {
            "supplier_code": "SUP-PM-001",
            "supplier_name": "Paint & More Main Store",
            "short_name": "Paint & More",
            "city": "Ho Chi Minh City",
            "rating": 4.6,
            "is_active": True,
        })
        prices = [680000, 540000, 1850000, 430000, 790000]
        for product, price in zip(self.rows["afp_products"], prices):
            self.insert("afp_product_suppliers", {
                "product_id": product["id"],
                "supplier_id": supplier["id"],
                "unit_price": price,
                "currency": "VND",
                "price_status": "quoted",
                "stock_qty": 24,
                "min_order_qty": 1,
                "delivery_days": 2,
                "is_available": True,
            })


mock_supabase = MockSupabase()





