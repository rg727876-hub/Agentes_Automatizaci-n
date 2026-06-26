"""Router de catálogo: productos y proveedores."""
from fastapi import APIRouter

from config import DB_PATH
from api.utils import call_tool
from tools.inventory_tools import get_all_products
from tools.supplier_tools import get_all_suppliers

router = APIRouter(tags=["catalog"])


@router.get("/products")
def products(category: str | None = None):
    data = call_tool(get_all_products, DB_PATH, category) or []
    return {"products": data}


@router.get("/suppliers")
def suppliers():
    data = call_tool(get_all_suppliers, DB_PATH) or []
    return {"suppliers": data}
