# AFP Paint Suggestion App — Effective Product Recommendation Flow

## 1. Goal

This guide explains how to build an effective product suggestion flow for the AFP Paint/Revit BOM app.

The system should take Revit building data, generate paint BOM items, search the product database, rank suitable products, ask the LLM to explain the suggestion, then let the user approve the final product.

The most important rule:

```text
Database + vector search choose product.
LLM explains why the product is suitable.
User approves the final product.
```

Do not let the LLM freely choose products from all products. That can create wrong suggestions.

---

## 2. Final System Flow

```text
Revit JSON
   ↓
Import project / rooms / elements
   ↓
Generate BOM items
   ↓
Build product requirement
   ↓
SQL hard filter
   ↓
Vector search
   ↓
Supplier / price / stock check
   ↓
Ranking score
   ↓
Save suggestions
   ↓
LLM explanation
   ↓
User approve / reject / replace
   ↓
Export approved BOM
```

---

## 3. Why This Flow Works

### SQL hard filter

SQL prevents technically wrong products.

Example:

Bathroom wall should not suggest:

```text
PRO 2080 sealant
K7781 metal paint
One Coat 365 exterior facade paint
```

SQL checks exact fields:

```text
product_type
features
usage_areas
recommended_for_tags
not_recommended_for_tags
status
```

### Vector search

Vector search helps when the wording is different.

Example user/Revit query:

```text
High humidity toilet wall needs moisture protection
```

Vector search can understand this is close to:

```text
bathroom wall
wet area wall
waterproof
mold resistant
damp wall
```

### Ranking

Ranking chooses the best option based on:

```text
semantic match
required feature match
preferred feature match
price
stock
delivery
supplier rating
```

### LLM explanation

LLM turns technical data into clear explanation for architect, QS, or project owner.

---

## 4. Necessary Tables

### Core Revit/BOM tables

```text
afp_projects
afp_levels
afp_rooms
afp_revit_elements
afp_bom_items
```

### Product suggestion tables

```text
afp_products
afp_suppliers
afp_product_suppliers
afp_material_requirement_rules
afp_bom_product_suggestions
afp_bom_exports
```

---

## 5. Clean afp_products Table Design

Keep only columns needed for search, vector, and explanation.

```sql
CREATE TABLE IF NOT EXISTS public.afp_products (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  sku TEXT NOT NULL UNIQUE,
  product_name TEXT NOT NULL,
  brand TEXT,
  raw_category TEXT,
  product_type TEXT,

  usage_areas JSONB DEFAULT '[]'::jsonb,
  features JSONB DEFAULT '[]'::jsonb,
  room_suitability JSONB DEFAULT '[]'::jsonb,
  surface_types JSONB DEFAULT '[]'::jsonb,

  package_unit TEXT,
  package_size NUMERIC,
  coverage_m2_per_liter NUMERIC,
  package_area_m2 NUMERIC,

  status TEXT DEFAULT 'active',
  source_url TEXT,

  function_description TEXT,
  effective_reason TEXT,
  recommended_for_tags JSONB DEFAULT '[]'::jsonb,
  not_recommended_for_tags JSONB DEFAULT '[]'::jsonb,

  embedding_text TEXT,
  embedding vector(1024),

  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now()
);
```

---

## 6. Product Data Meaning

### product_type

This is the main technical class.

Examples:

```text
interior_wall_paint
exterior_wall_paint
waterproofing_paint
sealant
universal_primer
metal_primer_coating
industrial_protective_coating
decorative_effect_paint
textured_wall_coating
```

### usage_areas

Where the product can be used.

```json
["bathroom_wall", "wet_area_wall", "damp_wall"]
```

### features

What the product can do.

```json
["waterproof", "mold_resistant", "low_odor", "easy_clean"]
```

### recommended_for_tags

Strong suggestion tags.

```json
["bathroom_wall", "humidity_resistance", "mold_resistance"]
```

### not_recommended_for_tags

Use this to avoid wrong suggestions.

```json
["metal_surface", "dry_bedroom_wall", "sealant_work"]
```

### function_description

Clear product function.

```text
Sơn chống thấm ngược dùng cho tường bị thấm, tường ẩm hoặc khu vực có nguy cơ nước thấm từ phía sau bề mặt.
```

### effective_reason

Why the product is effective.

```text
Hiệu quả vì tập trung vào chống thấm ngược, dùng cho tường ẩm và hỗ trợ ngăn rêu mốc trong khu vực có độ ẩm cao.
```

---

## 7. Product Search Indexes

```sql
CREATE INDEX IF NOT EXISTS idx_afp_products_status
ON public.afp_products(status);

CREATE INDEX IF NOT EXISTS idx_afp_products_product_type
ON public.afp_products(product_type);

CREATE INDEX IF NOT EXISTS idx_afp_products_usage_areas_gin
ON public.afp_products USING GIN (usage_areas);

CREATE INDEX IF NOT EXISTS idx_afp_products_features_gin
ON public.afp_products USING GIN (features);

CREATE INDEX IF NOT EXISTS idx_afp_products_room_suitability_gin
ON public.afp_products USING GIN (room_suitability);

CREATE INDEX IF NOT EXISTS idx_afp_products_surface_types_gin
ON public.afp_products USING GIN (surface_types);

CREATE INDEX IF NOT EXISTS idx_afp_products_recommended_for_tags_gin
ON public.afp_products USING GIN (recommended_for_tags);

CREATE INDEX IF NOT EXISTS idx_afp_products_not_recommended_for_tags_gin
ON public.afp_products USING GIN (not_recommended_for_tags);
```

---

## 8. Revit JSON Input

Revit JSON should contain building and surface data only.

Do not include product suggestions in Revit JSON.

```json
{
  "project": {
    "project_code": "AFP-DEMO-001",
    "project_name": "Villa Demo"
  },
  "rooms": [
    {
      "room_id": "R-101",
      "name": "Master Bathroom",
      "level": "Level 1",
      "area_m2": 12.5,
      "height_m": 3.0,
      "surfaces": {
        "wall": {
          "area_m2": 32.5,
          "substrate": "concrete",
          "condition": "new",
          "finish_type": "interior_paint"
        }
      },
      "requirements": {
        "humidity_resistance": true,
        "mold_resistance": true,
        "washability": "high",
        "color_preference": "neutral white"
      }
    }
  ]
}
```

---

## 9. Generate BOM Items

From Revit surface area, create BOM item.

```json
{
  "item_name": "Paint wall - Master Bathroom",
  "category": "paint",
  "surface": "wall",
  "raw_material_name": "concrete wall",
  "quantity": 32.5,
  "unit": "m2",
  "waste_factor": 1.1,
  "formula_type": "surface_area_with_waste"
}
```

Quantity formula:

```text
required_area = surface_area_m2 × waste_factor
required_area = 32.5 × 1.1 = 35.75 m²
```

Save into:

```text
afp_bom_items
```

---

## 10. Material Requirement Rules

Create rules that convert BOM item context into product requirement.

```sql
CREATE TABLE IF NOT EXISTS public.afp_material_requirement_rules (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  rule_code TEXT NOT NULL UNIQUE,
  bom_category TEXT NOT NULL,
  room_type TEXT DEFAULT 'Any',
  surface TEXT DEFAULT 'Any',

  required_product_type TEXT NOT NULL,
  usage_area TEXT NOT NULL,

  required_features JSONB DEFAULT '[]'::jsonb,
  preferred_features JSONB DEFAULT '[]'::jsonb,

  waste_factor NUMERIC DEFAULT 1.10,
  priority INTEGER DEFAULT 1,
  description TEXT,
  is_active BOOLEAN DEFAULT true,

  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now()
);
```

Example rules:

```sql
INSERT INTO public.afp_material_requirement_rules (
  rule_code,
  bom_category,
  room_type,
  surface,
  required_product_type,
  usage_area,
  required_features,
  preferred_features,
  waste_factor,
  priority,
  description
)
VALUES
(
  'BATHROOM_WALL_WATERPROOF',
  'paint',
  'bathroom',
  'wall',
  'waterproofing_paint',
  'bathroom_wall',
  '["waterproof", "mold_resistant"]'::jsonb,
  '["low_odor", "easy_clean", "humidity_resistant"]'::jsonb,
  1.15,
  10,
  'Bathroom walls need waterproofing and mold resistance.'
),
(
  'INTERIOR_DRY_WALL',
  'paint',
  'Any',
  'wall',
  'interior_wall_paint',
  'interior_wall',
  '["low_odor"]'::jsonb,
  '["easy_clean", "low_voc", "color_retention"]'::jsonb,
  1.10,
  5,
  'Dry interior walls need low-odor interior wall paint.'
),
(
  'EXTERIOR_FACADE',
  'paint',
  'Any',
  'exterior_wall',
  'exterior_wall_paint',
  'exterior_facade',
  '["uv_resistant", "weather_resistant"]'::jsonb,
  '["water_resistant", "mold_resistant", "color_retention"]'::jsonb,
  1.15,
  8,
  'Exterior facade needs UV and weather resistant paint.'
)
ON CONFLICT (rule_code)
DO UPDATE SET
  required_product_type = EXCLUDED.required_product_type,
  usage_area = EXCLUDED.usage_area,
  required_features = EXCLUDED.required_features,
  preferred_features = EXCLUDED.preferred_features,
  waste_factor = EXCLUDED.waste_factor,
  priority = EXCLUDED.priority,
  description = EXCLUDED.description,
  updated_at = now();
```

---

## 11. Build Product Requirement

Backend function:

```python
def build_product_requirement(bom_item: dict, room: dict | None = None) -> dict:
    room_type = (room or {}).get("room_type", "")
    surface = bom_item.get("surface", "")

    if "bathroom" in room_type.lower() and surface == "wall":
        return {
            "required_product_type": "waterproofing_paint",
            "required_tags": ["bathroom_wall", "wet_area_wall", "humidity_resistance"],
            "required_features": ["waterproof", "mold_resistant"],
            "preferred_features": ["low_odor", "easy_clean"],
            "waste_factor": 1.15
        }

    if surface in ["exterior_wall", "facade"]:
        return {
            "required_product_type": "exterior_wall_paint",
            "required_tags": ["exterior_facade", "weather_resistance", "uv_resistance"],
            "required_features": ["uv_resistant", "weather_resistant"],
            "preferred_features": ["water_resistant", "color_retention"],
            "waste_factor": 1.15
        }

    return {
        "required_product_type": "interior_wall_paint",
        "required_tags": ["interior_wall", "dry_interior_wall"],
        "required_features": ["low_odor"],
        "preferred_features": ["easy_clean", "low_voc"],
        "waste_factor": 1.10
    }
```

---

## 12. SQL Hard Filter

Example bathroom wall query:

```sql
SELECT
  id,
  sku,
  product_name,
  product_type,
  features,
  recommended_for_tags,
  not_recommended_for_tags,
  function_description,
  effective_reason
FROM public.afp_products
WHERE status = 'active'
  AND product_type = 'waterproofing_paint'
  AND recommended_for_tags ?| ARRAY[
    'bathroom_wall',
    'wet_area_wall',
    'humidity_resistance'
  ]
  AND features ?| ARRAY[
    'waterproof',
    'mold_resistant'
  ]
  AND NOT not_recommended_for_tags ? 'bathroom_wall';
```

Expected product:

```text
WATERTITE
```

---

## 13. Embedding Text

Build embedding_text for each product.

```sql
UPDATE public.afp_products
SET embedding_text =
  COALESCE(product_name, '') || '. ' ||
  'Brand: ' || COALESCE(brand, '') || '. ' ||
  'Category: ' || COALESCE(raw_category, '') || '. ' ||
  'Product type: ' || COALESCE(product_type, '') || '. ' ||
  'Usage areas: ' || COALESCE(usage_areas::text, '') || '. ' ||
  'Features: ' || COALESCE(features::text, '') || '. ' ||
  'Room suitability: ' || COALESCE(room_suitability::text, '') || '. ' ||
  'Surface types: ' || COALESCE(surface_types::text, '') || '. ' ||
  'Recommended for: ' || COALESCE(recommended_for_tags::text, '') || '. ' ||
  'Not recommended for: ' || COALESCE(not_recommended_for_tags::text, '') || '. ' ||
  'Function: ' || COALESCE(function_description, '') || '. ' ||
  'Effective reason: ' || COALESCE(effective_reason, '') || '.'
WHERE status = 'active';
```

---

## 14. Vectorize Products With NVIDIA Embedding

Use input_type = passage for product data.

```python
import os
import time
from dotenv import load_dotenv
from openai import OpenAI
from supabase import create_client

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)

nvidia = OpenAI(
    api_key=os.getenv("NVIDIA_API_KEY"),
    base_url="https://integrate.api.nvidia.com/v1"
)

EMBED_MODEL = os.getenv("NVIDIA_EMBED_MODEL", "nvidia/nv-embedqa-e5-v5")


def create_product_embedding(text: str) -> list[float]:
    response = nvidia.embeddings.create(
        model=EMBED_MODEL,
        input=[text],
        extra_body={
            "input_type": "passage",
            "truncate": "END"
        }
    )
    return [float(x) for x in response.data[0].embedding]


def vectorize_products():
    result = (
        supabase
        .table("afp_products")
        .select("id, sku, product_name, embedding_text")
        .eq("status", "active")
        .is_("embedding", "null")
        .execute()
    )

    products = result.data or []

    for product in products:
        text = product.get("embedding_text")
        if not text:
            print("Skip missing text:", product.get("sku"))
            continue

        print("Embedding:", product["sku"], product["product_name"])
        embedding = create_product_embedding(text)

        (
            supabase
            .table("afp_products")
            .update({"embedding": embedding})
            .eq("id", product["id"])
            .execute()
        )

        time.sleep(0.2)


if __name__ == "__main__":
    vectorize_products()
```

---

## 15. Hybrid Search RPC

SQL filter + vector search.

```sql
CREATE OR REPLACE FUNCTION public.match_products_hybrid(
  query_embedding vector(1024),
  match_product_type TEXT DEFAULT NULL,
  match_tags TEXT[] DEFAULT '{}',
  match_features TEXT[] DEFAULT '{}',
  match_count INT DEFAULT 5
)
RETURNS TABLE (
  id UUID,
  sku TEXT,
  product_name TEXT,
  product_type TEXT,
  raw_category TEXT,
  function_description TEXT,
  effective_reason TEXT,
  semantic_score DOUBLE PRECISION
)
LANGUAGE sql
STABLE
AS $$
  SELECT
    p.id,
    p.sku,
    p.product_name,
    p.product_type,
    p.raw_category,
    p.function_description,
    p.effective_reason,
    1 - (p.embedding <=> query_embedding) AS semantic_score
  FROM public.afp_products p
  WHERE p.status = 'active'
    AND p.embedding IS NOT NULL
    AND (
      match_product_type IS NULL
      OR p.product_type = match_product_type
    )
    AND (
      cardinality(match_tags) = 0
      OR p.recommended_for_tags ?| match_tags
      OR p.usage_areas ?| match_tags
      OR p.room_suitability ?| match_tags
    )
    AND (
      cardinality(match_features) = 0
      OR p.features ?| match_features
    )
  ORDER BY p.embedding <=> query_embedding
  LIMIT match_count;
$$;
```

---

## 16. Search Products From BOM Item

Use input_type = query for BOM/user query.

```python
def create_query_embedding(nvidia, query: str) -> list[float]:
    response = nvidia.embeddings.create(
        model=EMBED_MODEL,
        input=[query],
        extra_body={
            "input_type": "query",
            "truncate": "END"
        }
    )
    return [float(x) for x in response.data[0].embedding]


def build_bom_query_text(bom_item: dict, requirement: dict) -> str:
    return f"""
    BOM item: {bom_item.get("item_name")}
    Category: {bom_item.get("category")}
    Surface: {bom_item.get("surface")}
    Raw material: {bom_item.get("raw_material_name")}
    Quantity: {bom_item.get("quantity")} {bom_item.get("unit")}

    Required product type: {requirement.get("required_product_type")}
    Required tags: {requirement.get("required_tags")}
    Required features: {requirement.get("required_features")}
    Preferred features: {requirement.get("preferred_features")}
    """


def hybrid_search_products(supabase, query_embedding, requirement):
    result = (
        supabase
        .rpc(
            "match_products_hybrid",
            {
                "query_embedding": query_embedding,
                "match_product_type": requirement["required_product_type"],
                "match_tags": requirement["required_tags"],
                "match_features": requirement["required_features"],
                "match_count": 5
            }
        )
        .execute()
    )

    return result.data or []
```

---

## 17. Attach Supplier / Price / Stock

After product candidates are found, join supplier data.

```sql
SELECT
  p.id AS product_id,
  p.sku,
  p.product_name,
  p.product_type,
  p.function_description,
  ps.id AS product_supplier_id,
  s.id AS supplier_id,
  s.supplier_name,
  s.rating,
  ps.unit_price,
  ps.currency,
  ps.stock_qty,
  ps.delivery_days,
  ps.is_available
FROM public.afp_products p
JOIN public.afp_product_suppliers ps
  ON ps.product_id = p.id
JOIN public.afp_suppliers s
  ON s.id = ps.supplier_id
WHERE p.id = ANY(:product_ids)
  AND ps.is_available = true;
```

---

## 18. Ranking Formula

Use this score:

```text
final_score =
semantic_score × 0.30
+ feature_score × 0.30
+ price_score × 0.15
+ stock_score × 0.15
+ delivery_score × 0.10
```

Feature score:

```python
def calculate_feature_score(product: dict, requirement: dict) -> float:
    product_features = set(product.get("features", []))
    required = set(requirement.get("required_features", []))
    preferred = set(requirement.get("preferred_features", []))

    required_score = 1.0 if not required else len(product_features & required) / len(required)
    preferred_score = 0.0 if not preferred else len(product_features & preferred) / len(preferred)

    return min((required_score * 0.75) + (preferred_score * 0.25), 1.0)
```

Stock score:

```python
def calculate_stock_score(stock_qty: float | None, required_qty: float) -> float:
    if stock_qty is None:
        return 0.5
    if stock_qty >= required_qty:
        return 1.0
    if stock_qty > 0:
        return 0.6
    return 0.0
```

Delivery score:

```python
def calculate_delivery_score(delivery_days: int | None) -> float:
    if delivery_days is None:
        return 0.5
    if delivery_days <= 2:
        return 1.0
    if delivery_days <= 5:
        return 0.8
    if delivery_days <= 10:
        return 0.5
    return 0.2
```

---

## 19. Save Suggestions

Save ranked results into afp_bom_product_suggestions.

Important columns:

```text
bom_item_id
product_id
supplier_id
product_supplier_id
rank_no
is_best_option
hard_filter_pass
required_match
preferred_match
semantic_score
feature_score
price_score
stock_score
delivery_score
supplier_score
final_score
estimated_required_package_qty
estimated_total_cost
suggestion_status
reason
```

---

## 20. LLM Explanation

LLM should receive only ranked candidate products.

Prompt:

```python
def build_llm_explanation_prompt(context: dict) -> str:
    return f"""
You are an assistant for a Revit paint BOM product suggestion system.

Your job:
Explain why the already-ranked product is suitable.

Rules:
- Use only the provided JSON.
- Do not invent product information.
- Do not change product ranking.
- Do not invent price, stock, delivery, or supplier.
- If data is missing, say it is missing.
- Explain clearly for architect, QS engineer, and project owner.
- Return JSON only.

Output format:
{{
  "summary": "",
  "why_it_matches": [],
  "why_it_is_effective": [],
  "commercial_reason": [],
  "warnings": [],
  "approval_recommendation": ""
}}

Data:
{context}
"""
```

---

## 21. User Approval Flow

Frontend should show:

```text
BOM item: Paint wall - Master Bathroom
Suggested product: WATERTITE
Reason: Waterproofing + mold resistance + wet area suitable
Estimated quantity: 2 buckets
Estimated cost: 4,700,000 VND
Status: Suggested
```

User actions:

```text
Approve
Reject
Replace product
```

Approve SQL:

```sql
UPDATE public.afp_bom_product_suggestions
SET suggestion_status = 'approved',
    approved_by = :user_email,
    approved_at = now()
WHERE id = :suggestion_id;
```

---

## 22. Export Approved BOM

Export only approved suggestions.

```sql
SELECT
  p.project_name,
  r.room_name,
  b.item_name,
  b.surface,
  b.quantity,
  b.unit,
  prod.product_name,
  prod.product_type,
  s.supplier_name,
  sug.estimated_required_package_qty,
  sug.estimated_total_cost,
  sug.currency,
  sug.reason
FROM public.afp_bom_product_suggestions sug
JOIN public.afp_bom_items b
  ON b.id = sug.bom_item_id
JOIN public.afp_projects p
  ON p.id = b.project_id
LEFT JOIN public.afp_rooms r
  ON r.id = b.room_id
JOIN public.afp_products prod
  ON prod.id = sug.product_id
JOIN public.afp_suppliers s
  ON s.id = sug.supplier_id
WHERE sug.suggestion_status = 'approved'
  AND p.id = :project_id
ORDER BY r.room_name, b.item_name;
```

---

## 23. API Endpoints

```text
POST /projects/import-revit-json
POST /projects/{project_id}/generate-bom
POST /bom-items/{bom_item_id}/suggest-products
POST /suggestions/{suggestion_id}/approve
POST /suggestions/{suggestion_id}/reject
POST /projects/{project_id}/export-bom
```

---

## 24. Backend Folder Structure

```text
backend/
├── app/
│   ├── main.py
│   ├── core/
│   │   ├── config.py
│   │   └── supabase.py
│   ├── services/
│   │   ├── revit_import_service.py
│   │   ├── bom_service.py
│   │   ├── requirement_service.py
│   │   ├── embedding_service.py
│   │   ├── product_search_service.py
│   │   ├── ranking_service.py
│   │   ├── llm_explanation_service.py
│   │   └── export_service.py
│   ├── routes/
│   │   ├── projects.py
│   │   ├── bom.py
│   │   ├── suggestions.py
│   │   └── exports.py
│   └── schemas/
│       ├── project_schema.py
│       ├── bom_schema.py
│       └── suggestion_schema.py
```

---

## 25. Frontend Pages

```text
/projects
/projects/:id
/projects/:id/bom
/bom-items/:id/suggestions
/exports
```

Suggestion card should show:

```text
Product name
Product type
Function
Why effective
Matched requirements
Price
Stock
Delivery
Final score
LLM explanation
Approve / Reject / Replace buttons
```

---

## 26. Final Checklist

Database:

```text
[ ] afp_products has clean columns
[ ] all 24 products inserted
[ ] function_description filled
[ ] effective_reason filled
[ ] recommended_for_tags filled
[ ] not_recommended_for_tags filled
[ ] embedding_text built
[ ] embedding generated
[ ] match_products_hybrid RPC created
```

Backend:

```text
[ ] import Revit JSON
[ ] generate BOM
[ ] build requirement
[ ] create query embedding
[ ] hybrid search
[ ] attach supplier data
[ ] rank products
[ ] save suggestions
[ ] LLM explanation
[ ] approve / reject
[ ] export approved BOM
```

Frontend:

```text
[ ] project upload page
[ ] BOM table page
[ ] suggestion detail page
[ ] LLM explanation card
[ ] approve/reject controls
[ ] export button
```

---

## 27. Best Rule To Remember

```text
Revit tells what the building needs.
BOM calculates quantity.
SQL removes wrong products.
Vector search finds the closest valid product.
Ranking chooses the best option.
LLM explains clearly.
User approves.
Export BOM.
```
