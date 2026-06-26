"""Router del dashboard: KPIs y datos para los gráficos.

Llama a las herramientas de datos directamente (sin pasar por el LLM): son
consultas rápidas a la base de datos.
"""
from fastapi import APIRouter

from config import DB_PATH
from api.utils import call_tool
from tools.inventory_tools import (
    get_inventory_value,
    get_active_alerts,
    get_low_stock_products,
    get_out_of_stock_products,
)
from tools.sales_tools import (
    get_revenue_summary,
    get_top_selling_products,
    get_sales_by_category,
    get_sales_by_period,
)
from tools.order_tools import get_pending_orders

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard")
def dashboard():
    inv = call_tool(get_inventory_value, DB_PATH) or {}
    revenue = call_tool(get_revenue_summary, DB_PATH, 30) or {}
    top = call_tool(get_top_selling_products, DB_PATH, 30, 8) or []
    by_cat = call_tool(get_sales_by_category, DB_PATH, 30) or []
    daily = call_tool(get_sales_by_period, DB_PATH, 30) or []
    alerts = call_tool(get_active_alerts, DB_PATH) or []
    low_stock = call_tool(get_low_stock_products, DB_PATH) or []
    out_stock = call_tool(get_out_of_stock_products, DB_PATH) or []
    pending = call_tool(get_pending_orders, DB_PATH) or {}

    # La serie diaria viene en orden descendente: la invertimos para el gráfico.
    daily_sorted = sorted(daily, key=lambda r: r.get("sale_date", ""))

    return {
        "kpis": {
            "total_revenue": revenue.get("total_revenue", 0),
            "gross_profit": revenue.get("gross_profit", 0),
            "total_units_sold": revenue.get("total_units", 0),
            "total_transactions": revenue.get("total_transactions", 0),
            "inventory_retail_value": inv.get("total_retail_value", 0),
            "inventory_units": inv.get("total_units", 0),
            "active_alerts": len(alerts),
            "out_of_stock": len(out_stock),
            "low_stock": len(low_stock),
            "pending_orders": pending.get("total_orders", 0),
            "committed_spend": pending.get("total_committed_spend", 0),
        },
        "charts": {
            "sales_daily": {
                "labels": [r.get("sale_date", "")[5:] for r in daily_sorted],
                "revenue": [round(r.get("total_revenue", 0) or 0, 2) for r in daily_sorted],
                "units": [r.get("total_qty", 0) or 0 for r in daily_sorted],
            },
            "sales_by_category": {
                "labels": [r.get("category", "") for r in by_cat],
                "revenue": [round(r.get("total_revenue", 0) or 0, 2) for r in by_cat],
            },
            "inventory_by_category": {
                "labels": [r.get("category", "") for r in inv.get("by_category", [])],
                "retail_value": [round(r.get("retail_value", 0) or 0, 2) for r in inv.get("by_category", [])],
            },
            "top_products": {
                "labels": [r.get("name", "") for r in top],
                "units": [r.get("total_sold", 0) or 0 for r in top],
            },
        },
        "alerts": alerts,
        "low_stock": low_stock,
        "out_of_stock": out_stock,
        "pending_orders": pending.get("pending_orders", []),
    }
