import json
import sqlite3
from database import get_connection


def get_all_products(db_path: str, category: str = None) -> str:
    conn = get_connection(db_path)
    try:
        if category:
            rows = conn.execute(
                "SELECT p.id, p.sku, p.name, p.category, p.unit_price, p.cost_price, i.quantity "
                "FROM products p JOIN inventory i ON p.id = i.product_id "
                "WHERE p.category = ? ORDER BY p.name",
                (category,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT p.id, p.sku, p.name, p.category, p.unit_price, p.cost_price, i.quantity "
                "FROM products p JOIN inventory i ON p.id = i.product_id ORDER BY p.category, p.name"
            ).fetchall()
        return json.dumps([dict(r) for r in rows], ensure_ascii=False)
    finally:
        conn.close()


def get_product_inventory(db_path: str, product_id: int = None, sku: str = None) -> str:
    conn = get_connection(db_path)
    try:
        if product_id:
            row = conn.execute(
                "SELECT p.id, p.sku, p.name, p.category, p.unit_price, p.cost_price, "
                "p.reorder_point, p.reorder_quantity, i.quantity, i.reserved_quantity, i.warehouse_location "
                "FROM products p JOIN inventory i ON p.id = i.product_id WHERE p.id = ?",
                (product_id,)
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT p.id, p.sku, p.name, p.category, p.unit_price, p.cost_price, "
                "p.reorder_point, p.reorder_quantity, i.quantity, i.reserved_quantity, i.warehouse_location "
                "FROM products p JOIN inventory i ON p.id = i.product_id WHERE p.sku = ?",
                (sku,)
            ).fetchone()
        if not row:
            return json.dumps({"error": "Producto no encontrado"})
        return json.dumps(dict(row), ensure_ascii=False)
    finally:
        conn.close()


def get_low_stock_products(db_path: str) -> str:
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT p.id, p.sku, p.name, p.category, p.reorder_point, i.quantity, "
            "(i.quantity - p.reorder_point) as stock_gap "
            "FROM products p JOIN inventory i ON p.id = i.product_id "
            "WHERE i.quantity > 0 AND i.quantity <= p.reorder_point "
            "ORDER BY stock_gap ASC"
        ).fetchall()
        return json.dumps([dict(r) for r in rows], ensure_ascii=False)
    finally:
        conn.close()


def get_out_of_stock_products(db_path: str) -> str:
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT p.id, p.sku, p.name, p.category, p.unit_price, p.reorder_quantity "
            "FROM products p JOIN inventory i ON p.id = i.product_id "
            "WHERE i.quantity = 0 ORDER BY p.category, p.name"
        ).fetchall()
        return json.dumps([dict(r) for r in rows], ensure_ascii=False)
    finally:
        conn.close()


def update_stock_quantity(db_path: str, product_id: int, new_quantity: int, reason: str = "") -> str:
    conn = get_connection(db_path)
    try:
        old = conn.execute("SELECT quantity FROM inventory WHERE product_id = ?", (product_id,)).fetchone()
        if not old:
            return json.dumps({"error": "Producto no encontrado en inventario"})
        conn.execute(
            "UPDATE inventory SET quantity = ?, last_updated = datetime('now') WHERE product_id = ?",
            (new_quantity, product_id)
        )
        conn.commit()
        return json.dumps({
            "success": True,
            "product_id": product_id,
            "old_quantity": old[0],
            "new_quantity": new_quantity,
            "reason": reason
        })
    finally:
        conn.close()


def get_inventory_value(db_path: str) -> str:
    conn = get_connection(db_path)
    try:
        total = conn.execute(
            "SELECT SUM(p.cost_price * i.quantity) as total_cost_value, "
            "SUM(p.unit_price * i.quantity) as total_retail_value, "
            "SUM(i.quantity) as total_units "
            "FROM products p JOIN inventory i ON p.id = i.product_id"
        ).fetchone()
        by_cat = conn.execute(
            "SELECT p.category, SUM(p.cost_price * i.quantity) as cost_value, "
            "SUM(p.unit_price * i.quantity) as retail_value, SUM(i.quantity) as units "
            "FROM products p JOIN inventory i ON p.id = i.product_id "
            "GROUP BY p.category ORDER BY retail_value DESC"
        ).fetchall()
        return json.dumps({
            "total_cost_value": round(total[0] or 0, 2),
            "total_retail_value": round(total[1] or 0, 2),
            "total_units": total[2] or 0,
            "by_category": [dict(r) for r in by_cat]
        }, ensure_ascii=False)
    finally:
        conn.close()


def get_active_alerts(db_path: str) -> str:
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT a.id, p.sku, p.name, a.alert_type, a.message, a.created_at "
            "FROM inventory_alerts a JOIN products p ON a.product_id = p.id "
            "WHERE a.is_resolved = 0 ORDER BY a.alert_type, a.created_at DESC"
        ).fetchall()
        return json.dumps([dict(r) for r in rows], ensure_ascii=False)
    finally:
        conn.close()


INVENTORY_TOOLS = [
    {
        "name": "get_all_products",
        "description": "Obtiene todos los productos con su stock actual. Opcionalmente filtra por categoría.",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "Categoría para filtrar: Electrónica, Ropa, Alimentos, Hogar, Deportes"}
            }
        }
    },
    {
        "name": "get_product_inventory",
        "description": "Obtiene el inventario detallado de un producto específico por ID o SKU.",
        "input_schema": {
            "type": "object",
            "properties": {
                "product_id": {"type": "integer", "description": "ID del producto"},
                "sku": {"type": "string", "description": "SKU del producto (ej: ELEC-001)"}
            }
        }
    },
    {
        "name": "get_low_stock_products",
        "description": "Obtiene todos los productos con stock bajo (en o por debajo del punto de reorden).",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "get_out_of_stock_products",
        "description": "Obtiene todos los productos sin stock (stock = 0).",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "update_stock_quantity",
        "description": "Actualiza la cantidad de stock de un producto.",
        "input_schema": {
            "type": "object",
            "properties": {
                "product_id": {"type": "integer", "description": "ID del producto"},
                "new_quantity": {"type": "integer", "description": "Nueva cantidad en stock"},
                "reason": {"type": "string", "description": "Motivo del ajuste"}
            },
            "required": ["product_id", "new_quantity"]
        }
    },
    {
        "name": "get_inventory_value",
        "description": "Calcula el valor total del inventario (costo y precio retail) por categoría.",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "get_active_alerts",
        "description": "Obtiene todas las alertas de inventario activas (sin stock, stock crítico, stock bajo).",
        "input_schema": {"type": "object", "properties": {}}
    },
]


def execute_inventory_tool(tool_name: str, tool_input: dict, db_path: str) -> str:
    tool_input["db_path"] = db_path
    dispatch = {
        "get_all_products": get_all_products,
        "get_product_inventory": get_product_inventory,
        "get_low_stock_products": get_low_stock_products,
        "get_out_of_stock_products": get_out_of_stock_products,
        "update_stock_quantity": update_stock_quantity,
        "get_inventory_value": get_inventory_value,
        "get_active_alerts": get_active_alerts,
    }
    func = dispatch.get(tool_name)
    if not func:
        return json.dumps({"error": f"Herramienta desconocida: {tool_name}"})
    kwargs = {k: v for k, v in tool_input.items()}
    return func(**kwargs)
