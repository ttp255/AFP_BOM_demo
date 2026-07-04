from fastapi import APIRouter

from app.db.supabase_client import supabase
from app.services.vector_service import index_products

router = APIRouter()


@router.get("/products")
def list_products():
    return supabase.table("afp_products").select("*").execute().data


@router.get("/suppliers")
def list_suppliers():
    return supabase.table("afp_suppliers").select("*").execute().data


@router.post("/products/reindex")
def reindex_products():
    indexed = index_products()
    return {"products_indexed": indexed}
