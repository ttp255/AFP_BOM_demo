from fastapi import APIRouter

from app.db.supabase_client import supabase
from app.services.vector_service import index_products

router = APIRouter()


@router.get("/products")
def list_products():
    page_size = 1000
    products = []
    start = 0

    while True:
        page = (
            supabase.table("afp_products")
            .select("*")
            .order("product_name")
            .range(start, start + page_size - 1)
            .execute()
            .data
            or []
        )
        products.extend(page)
        if len(page) < page_size:
            break
        start += page_size

    return products


@router.get("/suppliers")
def list_suppliers():
    return supabase.table("afp_suppliers").select("*").execute().data


@router.post("/products/reindex")
def reindex_products():
    indexed = index_products()
    return {"products_indexed": indexed}
