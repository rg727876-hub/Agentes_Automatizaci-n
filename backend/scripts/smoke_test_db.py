"""Prueba rápida de la conexión a Supabase/PostgreSQL y las tools.

Uso (desde la raíz del proyecto):
    1. Pon tu connection string de Supabase en .env (DATABASE_URL=...)
    2. Ejecuta:  python backend/scripts/smoke_test_db.py

Crea las tablas (si no existen), carga los datos de ejemplo (solo la primera
vez) y ejecuta una consulta representativa de cada módulo de herramientas.
No modifica datos.
"""
import os
import sys

# Permite ejecutar el script estando dentro de scripts/ (añade la raíz al path)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fix_ssl  # noqa: E402, F401  (configura SSL, debe importarse primero)
import json  # noqa: E402

from config import DATABASE_URL, DB_PATH  # noqa: E402
from database import setup_database
from tools.inventory_tools import get_low_stock_products, get_out_of_stock_products
from tools.sales_tools import get_revenue_summary
from tools.demand_tools import identify_stockout_risk, get_seasonal_analysis
from tools.supplier_tools import get_best_supplier_for_product
from tools.order_tools import get_pending_orders


def _show(label, raw):
    data = json.loads(raw)
    if isinstance(data, list):
        print(f"OK  {label}: {len(data)} fila(s)")
    else:
        print(f"OK  {label}: {list(data.keys())}")


def main():
    if not DATABASE_URL:
        print("ERROR: configura DATABASE_URL en .env antes de correr esta prueba.")
        return

    print("1) Creando tablas y datos de ejemplo (idempotente)...")
    setup_database(DB_PATH)
    print("   OK\n")

    print("2) Ejecutando una consulta por módulo:")
    _show("inventory.get_low_stock_products", get_low_stock_products(DB_PATH))
    _show("inventory.get_out_of_stock_products", get_out_of_stock_products(DB_PATH))
    _show("sales.get_revenue_summary", get_revenue_summary(DB_PATH, days=30))
    _show("demand.identify_stockout_risk", identify_stockout_risk(DB_PATH, risk_days=14))
    _show("demand.get_seasonal_analysis", get_seasonal_analysis(DB_PATH, product_id=13))
    _show("supplier.get_best_supplier_for_product", get_best_supplier_for_product(DB_PATH, product_id=1))
    _show("order.get_pending_orders", get_pending_orders(DB_PATH))

    print("\nTodo OK: la integración con Supabase funciona.")


if __name__ == "__main__":
    main()
