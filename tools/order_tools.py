import json
from datetime import datetime, timedelta
from database import get_connection


def create_purchase_order(db_path: str, supplier_id: int, product_id: int,
                        quantity: int, unit_cost: float, notes: str = "") -> str:
    conn = get_connection(db_path)
    try:
        supplier = conn.execute("SELECT lead_time_days FROM suppliers WHERE id = ?", (supplier_id,)).fetchone()
        if not supplier:
            return json.dumps({"error": "Proveedor no encontrado"})
        product = conn.execute("SELECT name FROM products WHERE id = ?", (product_id,)).fetchone()
        if not product:
            return json.dumps({"error": "Producto no encontrado"})
        total_cost = quantity * unit_cost
        expected_delivery = (datetime.now() + timedelta(days=supplier[0])).strftime("%Y-%m-%d")
        cursor = conn.execute(
            "INSERT INTO purchase_orders (supplier_id, product_id, quantity, unit_cost, total_cost, "
            "status, order_date, expected_delivery, notes) VALUES (?,?,?,?,?,'pendiente',datetime('now'),?,?)",
            (supplier_id, product_id, quantity, unit_cost, total_cost, expected_delivery, notes)
        )
        conn.commit()
        return json.dumps({
            "success": True,
            "order_id": cursor.lastrowid,
            "product_name": product[0],
            "quantity": quantity,
            "unit_cost": unit_cost,
            "total_cost": total_cost,
            "expected_delivery": expected_delivery,
            "status": "pendiente"
        }, ensure_ascii=False)
    finally:
        conn.close()


def get_purchase_orders(db_path: str, status: str = None, supplier_id: int = None) -> str:
    conn = get_connection(db_path)
    try:
        query = (
            "SELECT po.id, p.sku, p.name as product_name, s.name as supplier_name, "
            "po.quantity, po.unit_cost, po.total_cost, po.status, "
            "po.order_date, po.expected_delivery, po.received_date, po.notes "
            "FROM purchase_orders po "
            "JOIN products p ON po.product_id = p.id "
            "JOIN suppliers s ON po.supplier_id = s.id "
            "WHERE 1=1"
        )
        params = []
        if status:
            query += " AND po.status = ?"
            params.append(status)
        if supplier_id:
            query += " AND po.supplier_id = ?"
            params.append(supplier_id)
        query += " ORDER BY po.order_date DESC"
        rows = conn.execute(query, params).fetchall()
        return json.dumps([dict(r) for r in rows], ensure_ascii=False)
    finally:
        conn.close()


def update_order_status(db_path: str, order_id: int, new_status: str) -> str:
    conn = get_connection(db_path)
    try:
        order = conn.execute(
            "SELECT po.*, p.name as product_name FROM purchase_orders po "
            "JOIN products p ON po.product_id = p.id WHERE po.id = ?",
            (order_id,)
        ).fetchone()
        if not order:
            return json.dumps({"error": "Orden no encontrada"})

        valid_statuses = ["pendiente", "aprobado", "en_transito", "recibido", "cancelado"]
        if new_status not in valid_statuses:
            return json.dumps({"error": f"Estado inválido. Use: {', '.join(valid_statuses)}"})

        if new_status == "recibido":
            conn.execute(
                "UPDATE purchase_orders SET status = ?, received_date = date('now') WHERE id = ?",
                (new_status, order_id)
            )
            conn.execute(
                "UPDATE inventory SET quantity = quantity + ?, last_updated = datetime('now') "
                "WHERE product_id = ?",
                (order["quantity"], order["product_id"])
            )
            conn.execute(
                "DELETE FROM inventory_alerts WHERE product_id = ? AND is_resolved = 0",
                (order["product_id"],)
            )
        else:
            conn.execute("UPDATE purchase_orders SET status = ? WHERE id = ?", (new_status, order_id))

        conn.commit()
        return json.dumps({
            "success": True,
            "order_id": order_id,
            "product_name": order["product_name"],
            "old_status": order["status"],
            "new_status": new_status,
            "stock_updated": new_status == "recibido"
        }, ensure_ascii=False)
    finally:
        conn.close()


def calculate_reorder_point(db_path: str, product_id: int) -> str:
    conn = get_connection(db_path)
    try:
        product = conn.execute(
            "SELECT p.name, p.sku, p.reorder_point, p.reorder_quantity FROM products WHERE id = ?",
            (product_id,)
        ).fetchone()
        if not product:
            return json.dumps({"error": "Producto no encontrado"})
        supplier = conn.execute(
            "SELECT s.lead_time_days FROM product_suppliers ps "
            "JOIN suppliers s ON ps.supplier_id = s.id "
            "WHERE ps.product_id = ? AND ps.is_preferred = 1 LIMIT 1",
            (product_id,)
        ).fetchone()
        lead_time = supplier[0] if supplier else 7
        avg_daily = conn.execute(
            "SELECT COALESCE(CAST(SUM(quantity) AS REAL) / 30, 0) FROM sales "
            "WHERE product_id = ? AND sale_date >= ?",
            (product_id, (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"))
        ).fetchone()[0]

        safety_stock = round(avg_daily * lead_time * 0.5)
        calculated_reorder_point = round(avg_daily * lead_time + safety_stock)
        suggested_order_qty = round(avg_daily * 30)

        return json.dumps({
            "product_name": product[0],
            "sku": product[1],
            "current_reorder_point": product[2],
            "calculated_reorder_point": calculated_reorder_point,
            "safety_stock": safety_stock,
            "avg_daily_sales": round(avg_daily, 2),
            "supplier_lead_time_days": lead_time,
            "current_reorder_quantity": product[3],
            "suggested_order_quantity": suggested_order_qty
        }, ensure_ascii=False)
    finally:
        conn.close()


def get_pending_orders(db_path: str) -> str:
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT po.id, p.sku, p.name as product_name, s.name as supplier_name, "
            "po.quantity, po.total_cost, po.status, po.order_date, po.expected_delivery "
            "FROM purchase_orders po "
            "JOIN products p ON po.product_id = p.id "
            "JOIN suppliers s ON po.supplier_id = s.id "
            "WHERE po.status IN ('pendiente', 'aprobado', 'en_transito') "
            "ORDER BY po.expected_delivery ASC"
        ).fetchall()
        total_committed = sum(r["total_cost"] for r in rows)
        return json.dumps({
            "pending_orders": [dict(r) for r in rows],
            "total_orders": len(rows),
            "total_committed_spend": round(total_committed, 2)
        }, ensure_ascii=False)
    finally:
        conn.close()


ORDER_TOOLS = [
    {
        "name": "create_purchase_order",
        "description": "Crea una nueva orden de compra para reabastecer un producto de un proveedor.",
        "input_schema": {
            "type": "object",
            "properties": {
                "supplier_id": {"type": "integer", "description": "ID del proveedor"},
                "product_id": {"type": "integer", "description": "ID del producto a pedir"},
                "quantity": {"type": "integer", "description": "Cantidad a ordenar"},
                "unit_cost": {"type": "number", "description": "Costo unitario"},
                "notes": {"type": "string", "description": "Notas adicionales para la orden"}
            },
            "required": ["supplier_id", "product_id", "quantity", "unit_cost"]
        }
    },
    {
        "name": "get_purchase_orders",
        "description": "Obtiene las órdenes de compra, opcionalmente filtradas por estado o proveedor.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "description": "Estado: pendiente, aprobado, en_transito, recibido, cancelado"},
                "supplier_id": {"type": "integer", "description": "ID del proveedor para filtrar"}
            }
        }
    },
    {
        "name": "update_order_status",
        "description": "Actualiza el estado de una orden de compra. Si se marca como 'recibido', actualiza el stock automáticamente.",
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "integer", "description": "ID de la orden de compra"},
                "new_status": {"type": "string", "description": "Nuevo estado: pendiente, aprobado, en_transito, recibido, cancelado"}
            },
            "required": ["order_id", "new_status"]
        }
    },
    {
        "name": "calculate_reorder_point",
        "description": "Calcula el punto de reorden óptimo para un producto basado en ventas y lead time del proveedor.",
        "input_schema": {
            "type": "object",
            "properties": {
                "product_id": {"type": "integer", "description": "ID del producto"}
            },
            "required": ["product_id"]
        }
    },
    {
        "name": "get_pending_orders",
        "description": "Obtiene todas las órdenes de compra pendientes, aprobadas o en tránsito.",
        "input_schema": {"type": "object", "properties": {}}
    },
]


def execute_order_tool(tool_name: str, tool_input: dict, db_path: str) -> str:
    tool_input["db_path"] = db_path
    dispatch = {
        "create_purchase_order": create_purchase_order,
        "get_purchase_orders": get_purchase_orders,
        "update_order_status": update_order_status,
        "calculate_reorder_point": calculate_reorder_point,
        "get_pending_orders": get_pending_orders,
    }
    func = dispatch.get(tool_name)
    if not func:
        return json.dumps({"error": f"Herramienta desconocida: {tool_name}"})
    return func(**tool_input)
