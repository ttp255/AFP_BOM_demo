from datetime import datetime, timezone
from io import BytesIO
import json
import uuid

from openpyxl import Workbook

from app.db.supabase_client import supabase

EXPORT_COLUMNS = [
    "bom_code", "material", "product", "order_quantity", "supplier",
    "unit_price", "total_price", "currency",
]


def _number(value):
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _export_rows(project_id: str, scope: str) -> list[dict]:
    bom_items = supabase.table("afp_bom_items").select("*").eq("project_id", project_id).execute().data
    bom_by_id = {item["id"]: item for item in bom_items}
    suggestions = supabase.table("afp_bom_product_suggestions").select("*").execute().data
    suggestions = [
        row for row in suggestions
        if row.get("bom_item_id") in bom_by_id
        and (scope == "all_items" or (row.get("suggestion_status") or row.get("status")) == "approved")
    ]
    products = {row["id"]: row for row in supabase.table("afp_products").select("*").execute().data}
    suppliers = {row["id"]: row for row in supabase.table("afp_suppliers").select("*").execute().data}
    offers = supabase.table("afp_product_suppliers").select("*").execute().data
    offer_by_id = {row["id"]: row for row in offers}
    offer_by_product_supplier = {
        (row.get("product_id"), row.get("supplier_id")): row
        for row in offers
        if row.get("product_id") is not None and row.get("supplier_id") is not None
    }
    suggestion_by_bom = {}
    for suggestion in sorted(suggestions, key=lambda row: row.get("rank_no") or 999):
        suggestion_by_bom.setdefault(suggestion.get("bom_item_id"), suggestion)

    selected_items = bom_items if scope == "all_items" else [bom_by_id[bom_id] for bom_id in suggestion_by_bom]
    rows = []
    for item in selected_items:
        suggestion = suggestion_by_bom.get(item["id"], {})
        product = products.get(suggestion.get("product_id"), {})
        supplier = suppliers.get(suggestion.get("supplier_id"), {})
        offer = offer_by_id.get(suggestion.get("product_supplier_id"))
        if offer is None:
            offer = offer_by_product_supplier.get(
                (suggestion.get("product_id"), suggestion.get("supplier_id"))
            )
        order_quantity = suggestion.get("estimated_required_package_qty") or item.get("quantity") or ""
        unit_price = (offer or {}).get("unit_price")
        total_price = suggestion.get("estimated_total_cost") or suggestion.get("total_cost")
        if total_price in (None, ""):
            numeric_qty = _number(order_quantity)
            numeric_unit_price = _number(unit_price)
            if numeric_qty is not None and numeric_unit_price is not None:
                total_price = numeric_qty * numeric_unit_price
        rows.append({
            "bom_code": item.get("bom_code") or str(item.get("id", "")),
            "material": item.get("material_name") or item.get("item_name") or "Paint",
            "product": product.get("product_name") or "",
            "order_quantity": order_quantity,
            "supplier": supplier.get("supplier_name") or "",
            "unit_price": unit_price or "",
            "total_price": total_price or "",
            "currency": (offer or {}).get("currency") or suggestion.get("currency") or "VND",
        })
    return rows


def _total_price(rows: list[dict]) -> float:
    return sum(float(row.get("total_price") or 0) for row in rows)


def _excel_bytes(rows: list[dict]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "BOM"
    sheet.append([column.replace("_", " ").title() for column in EXPORT_COLUMNS])
    for row in rows:
        sheet.append([row.get(column, "") for column in EXPORT_COLUMNS])
    if rows:
        sheet.append([])
        total_column = EXPORT_COLUMNS.index("total_price")
        sheet.append([
            "Grand Total" if index == 0 else (
                _total_price(rows) if index == total_column else ""
            )
            for index in range(len(EXPORT_COLUMNS))
        ])
    sheet.freeze_panes = "A2"
    for column in sheet.columns:
        sheet.column_dimensions[column[0].column_letter].width = min(
            45, max(14, max(len(str(cell.value or "")) for cell in column) + 2)
        )
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def _pdf_bytes(rows: list[dict]) -> bytes:
    lines = ["AFP Paint - Bill of Materials", ""]
    for index, row in enumerate(rows, 1):
        lines.append(
            f"{index}. {row['bom_code']} | {row['material']} | {row['product']} | "
            f"Qty: {row['order_quantity']} | Unit: {row['unit_price']} {row['currency']} | "
            f"Total: {row['total_price']} {row['currency']}"
        )
    if not rows:
        lines.append("No BOM items matched the selected export scope.")
    else:
        lines.extend(["", f"Grand Total: {_total_price(rows)} {rows[0].get('currency') or 'VND'}"])
    text = "\n".join(lines).encode("latin-1", "replace").decode("latin-1")
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)").replace("\n", ") Tj T* (")
    stream = f"BT /F1 10 Tf 40 800 Td 12 TL ({escaped}) Tj ET"
    objects = [
        "1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj",
        "2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj",
        "3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj",
        "4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj",
        f"5 0 obj << /Length {len(stream.encode('latin-1'))} >> stream\n{stream}\nendstream endobj",
    ]
    pdf = b"%PDF-1.4\n"
    offsets = []
    for obj in objects:
        offsets.append(len(pdf))
        pdf += (obj + "\n").encode("latin-1")
    xref = len(pdf)
    pdf += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    pdf += b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets)
    pdf += f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()
    return pdf


def create_export(project_id: str, export_type: str = "json", scope: str = "approved_only") -> tuple[dict, bytes, str]:
    rows = _export_rows(project_id, scope)
    if scope == "approved_only" and not rows:
        raise ValueError("Approve at least one product suggestion before exporting approved items.")
    extension = {"excel": "xlsx", "pdf": "pdf", "json": "json"}[export_type]
    filename = f"afp-project-{project_id}-bom.{extension}"
    if export_type == "excel":
        content = _excel_bytes(rows)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif export_type == "pdf":
        content = _pdf_bytes(rows)
        media_type = "application/pdf"
    else:
        payload = {
            "rows": rows,
            "grand_total_price": _total_price(rows),
            "currency": rows[0].get("currency") if rows else "VND",
        }
        content = json.dumps(payload, ensure_ascii=False, indent=2, default=str).encode("utf-8")
        media_type = "application/json"
    total_cost = _total_price(rows)
    row = {
        "project_id": project_id,
        "export_code": "EXP-" + uuid.uuid4().hex[:8].upper(),
        "export_type": export_type,
        "export_scope": scope,
        "file_name": filename,
        "total_items": len(rows),
        "total_estimated_cost": total_cost,
        "currency": "VND",
        "export_status": "created",
        "exported_by": "admin",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "note": "Generated and downloaded by the export API.",
    }
    metadata = supabase.table("afp_bom_exports").insert(row).execute().data[0]
    return metadata, content, media_type