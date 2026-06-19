import json
from database import get_connection


def get_all_suppliers(db_path: str) -> str:
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT s.*, COUNT(DISTINCT ps.product_id) as products_supplied "
            "FROM suppliers s LEFT JOIN product_suppliers ps ON s.id = ps.supplier_id "
            "GROUP BY s.id ORDER BY s.reliability_score DESC"
        ).fetchall()
        return json.dumps([dict(r) for r in rows], ensure_ascii=False)
    finally:
        conn.close()


def get_supplier_details(db_path: str, supplier_id: int) -> str:
    conn = get_connection(db_path)
    try:
        supplier = conn.execute("SELECT * FROM suppliers WHERE id = ?", (supplier_id,)).fetchone()
        if not supplier:
            return json.dumps({"error": "Proveedor no encontrado"})
        products = conn.execute(
            "SELECT p.id, p.sku, p.name, p.category, ps.unit_cost, ps.min_order_quantity, ps.is_preferred "
            "FROM product_suppliers ps JOIN products p ON ps.product_id = p.id "
            "WHERE ps.supplier_id = ? ORDER BY p.category, p.name",
            (supplier_id,)
        ).fetchall()
        orders = conn.execute(
            "SELECT po.id, p.name as product_name, po.quantity, po.total_cost, po.status, po.order_date "
            "FROM purchase_orders po JOIN products p ON po.product_id = p.id "
            "WHERE po.supplier_id = ? ORDER BY po.order_date DESC LIMIT 5",
            (supplier_id,)
        ).fetchall()
        return json.dumps({
            "supplier": dict(supplier),
            "products": [dict(r) for r in products],
            "recent_orders": [dict(r) for r in orders]
        }, ensure_ascii=False)
    finally:
        conn.close()


def get_products_by_supplier(db_path: str, supplier_id: int) -> str:
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT p.id, p.sku, p.name, p.category, p.unit_price, "
            "ps.unit_cost, ps.min_order_quantity, ps.is_preferred, i.quantity as current_stock "
            "FROM product_suppliers ps "
            "JOIN products p ON ps.product_id = p.id "
            "JOIN inventory i ON p.id = i.product_id "
            "WHERE ps.supplier_id = ? ORDER BY p.category, p.name",
            (supplier_id,)
        ).fetchall()
        return json.dumps([dict(r) for r in rows], ensure_ascii=False)
    finally:
        conn.close()


def get_best_supplier_for_product(db_path: str, product_id: int) -> str:
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT s.id as supplier_id, s.name as supplier_name, s.lead_time_days, "
            "s.reliability_score, ps.unit_cost, ps.min_order_quantity, ps.is_preferred, "
            "(ps.unit_cost * (1 + (s.lead_time_days * 0.01)) * (1 / s.reliability_score)) as score "
            "FROM product_suppliers ps JOIN suppliers s ON ps.supplier_id = s.id "
            "WHERE ps.product_id = ? ORDER BY score ASC",
            (product_id,)
        ).fetchall()
        if not rows:
            return json.dumps({"error": "No se encontraron proveedores para este producto"})
        product = conn.execute("SELECT name, sku FROM products WHERE id = ?", (product_id,)).fetchone()
        return json.dumps({
            "product_name": product[0],
            "sku": product[1],
            "suppliers_ranked": [dict(r) for r in rows],
            "recommended_supplier": dict(rows[0])
        }, ensure_ascii=False)
    finally:
        conn.close()


def get_supplier_performance(db_path: str) -> str:
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT s.id, s.name, s.reliability_score, s.lead_time_days, "
            "COUNT(po.id) as total_orders, "
            "SUM(CASE WHEN po.status = 'recibido' THEN 1 ELSE 0 END) as completed_orders, "
            "SUM(po.total_cost) as total_spend "
            "FROM suppliers s LEFT JOIN purchase_orders po ON s.id = po.supplier_id "
            "GROUP BY s.id ORDER BY s.reliability_score DESC"
        ).fetchall()
        return json.dumps([dict(r) for r in rows], ensure_ascii=False)
    finally:
        conn.close()


SUPPLIER_TOOLS = [
    {
        "name": "get_all_suppliers",
        "description": "Obtiene todos los proveedores con su puntuación de confiabilidad y número de productos.",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "get_supplier_details",
        "description": "Obtiene información detallada de un proveedor: datos de contacto, productos y órdenes recientes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "supplier_id": {"type": "integer", "description": "ID del proveedor"}
            },
            "required": ["supplier_id"]
        }
    },
    {
        "name": "get_products_by_supplier",
        "description": "Obtiene todos los productos suministrados por un proveedor específico con costos y stock.",
        "input_schema": {
            "type": "object",
            "properties": {
                "supplier_id": {"type": "integer", "description": "ID del proveedor"}
            },
            "required": ["supplier_id"]
        }
    },
    {
        "name": "get_best_supplier_for_product",
        "description": "Determina el mejor proveedor para un producto considerando precio, lead time y confiabilidad.",
        "input_schema": {
            "type": "object",
            "properties": {
                "product_id": {"type": "integer", "description": "ID del producto"}
            },
            "required": ["product_id"]
        }
    },
    {
        "name": "get_supplier_performance",
        "description": "Obtiene métricas de rendimiento de todos los proveedores: órdenes, gasto total, confiabilidad.",
        "input_schema": {"type": "object", "properties": {}}
    },
]


def execute_supplier_tool(tool_name: str, tool_input: dict, db_path: str) -> str:
    tool_input["db_path"] = db_path
    dispatch = {
        "get_all_suppliers": get_all_suppliers,
        "get_supplier_details": get_supplier_details,
        "get_products_by_supplier": get_products_by_supplier,
        "get_best_supplier_for_product": get_best_supplier_for_product,
        "get_supplier_performance": get_supplier_performance,
    }
    func = dispatch.get(tool_name)
    if not func:
        return json.dumps({"error": f"Herramienta desconocida: {tool_name}"})
    return func(**tool_input)
