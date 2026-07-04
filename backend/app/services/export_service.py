from datetime import datetime, timezone
from io import BytesIO
import json
import uuid

from openpyxl import Workbook

from app.db.supabase_client import supabase

EXPORT_COLUMNS = [
    "bom_code", "material", "product", "order_quantity", "supplier",
    "total_cost", "currency",
]


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
    suggestion_by_bom = {}
    for suggestion in sorted(suggestions, key=lambda row: row.get("rank_no") or 999):
        suggestion_by_bom.setdefault(suggestion.get("bom_item_id"), suggestion)

    selected_items = bom_items if scope == "all_items" else [bom_by_id[bom_id] for bom_id in suggestion_by_bom]
    rows = []
    for item in selected_items:
        suggestion = suggestion_by_bom.get(item["id"], {})
        product = products.get(suggestion.get("product_id"), {})
        supplier = suppliers.get(suggestion.get("supplier_id"), {})
        rows.append({
            "bom_code": item.get("bom_code") or str(item.get("id", "")),
            "material": item.get("material_name") or item.get("item_name") or "Paint",
            "product": product.get("product_name") or "",
            "order_quantity": suggestion.get("estimated_required_package_qty") or item.get("quantity") or "",
            "supplier": supplier.get("supplier_name") or "",
            "total_cost": suggestion.get("estimated_total_cost") or suggestion.get("total_cost") or "",
            "currency": suggestion.get("currency") or "VND",
        })
    return rows


def _excel_bytes(rows: list[dict]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "BOM"
    sheet.append([column.replace("_", " ").title() for column in EXPORT_COLUMNS])
    for row in rows:
        sheet.append([row.get(column, "") for column in EXPORT_COLUMNS])
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
            f"Qty: {row['order_quantity']} | {row['total_cost']} {row['currency']}"
        )
    if not rows:
        lines.append("No BOM items matched the selected export scope.")
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
        content = json.dumps(rows, ensure_ascii=False, indent=2, default=str).encode("utf-8")
        media_type = "application/json"
    total_cost = sum(float(row.get("total_cost") or 0) for row in rows)
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
