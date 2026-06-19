import json
from datetime import datetime, timedelta
from database import get_connection


def get_sales_by_period(db_path: str, days: int = 30, product_id: int = None) -> str:
    conn = get_connection(db_path)
    try:
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        if product_id:
            rows = conn.execute(
                "SELECT s.sale_date, s.quantity, s.unit_price, s.total_amount, s.channel, p.name "
                "FROM sales s JOIN products p ON s.product_id = p.id "
                "WHERE s.product_id = ? AND s.sale_date >= ? ORDER BY s.sale_date DESC",
                (product_id, start_date)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT s.sale_date, SUM(s.quantity) as total_qty, SUM(s.total_amount) as total_revenue "
                "FROM sales s WHERE s.sale_date >= ? GROUP BY s.sale_date ORDER BY s.sale_date DESC",
                (start_date,)
            ).fetchall()
        return json.dumps([dict(r) for r in rows], ensure_ascii=False)
    finally:
        conn.close()


def get_top_selling_products(db_path: str, days: int = 30, limit: int = 10) -> str:
    conn = get_connection(db_path)
    try:
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        rows = conn.execute(
            "SELECT p.id, p.sku, p.name, p.category, SUM(s.quantity) as total_sold, "
            "SUM(s.total_amount) as total_revenue, AVG(s.unit_price) as avg_price "
            "FROM sales s JOIN products p ON s.product_id = p.id "
            "WHERE s.sale_date >= ? GROUP BY p.id ORDER BY total_sold DESC LIMIT ?",
            (start_date, limit)
        ).fetchall()
        return json.dumps([dict(r) for r in rows], ensure_ascii=False)
    finally:
        conn.close()


def get_sales_by_category(db_path: str, days: int = 30) -> str:
    conn = get_connection(db_path)
    try:
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        rows = conn.execute(
            "SELECT p.category, SUM(s.quantity) as total_units, "
            "SUM(s.total_amount) as total_revenue, COUNT(DISTINCT p.id) as products_sold "
            "FROM sales s JOIN products p ON s.product_id = p.id "
            "WHERE s.sale_date >= ? GROUP BY p.category ORDER BY total_revenue DESC",
            (start_date,)
        ).fetchall()
        return json.dumps([dict(r) for r in rows], ensure_ascii=False)
    finally:
        conn.close()


def get_revenue_summary(db_path: str, days: int = 30) -> str:
    conn = get_connection(db_path)
    try:
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        total = conn.execute(
            "SELECT SUM(s.total_amount) as total_revenue, SUM(s.quantity) as total_units, "
            "COUNT(*) as total_transactions, "
            "SUM(s.total_amount - (p.cost_price * s.quantity)) as gross_profit "
            "FROM sales s JOIN products p ON s.product_id = p.id WHERE s.sale_date >= ?",
            (start_date,)
        ).fetchone()
        by_channel = conn.execute(
            "SELECT channel, SUM(total_amount) as revenue, SUM(quantity) as units "
            "FROM sales WHERE sale_date >= ? GROUP BY channel ORDER BY revenue DESC",
            (start_date,)
        ).fetchall()
        return json.dumps({
            "period_days": days,
            "total_revenue": round(total[0] or 0, 2),
            "total_units": total[1] or 0,
            "total_transactions": total[2] or 0,
            "gross_profit": round(total[3] or 0, 2),
            "by_channel": [dict(r) for r in by_channel]
        }, ensure_ascii=False)
    finally:
        conn.close()


def get_product_sales_trend(db_path: str, product_id: int, days: int = 30) -> str:
    conn = get_connection(db_path)
    try:
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        product = conn.execute("SELECT name, sku FROM products WHERE id = ?", (product_id,)).fetchone()
        if not product:
            return json.dumps({"error": "Producto no encontrado"})
        rows = conn.execute(
            "SELECT sale_date, SUM(quantity) as daily_qty, SUM(total_amount) as daily_revenue "
            "FROM sales WHERE product_id = ? AND sale_date >= ? "
            "GROUP BY sale_date ORDER BY sale_date ASC",
            (product_id, start_date)
        ).fetchall()
        return json.dumps({
            "product_name": product[0],
            "sku": product[1],
            "period_days": days,
            "daily_trend": [dict(r) for r in rows]
        }, ensure_ascii=False)
    finally:
        conn.close()


SALES_TOOLS = [
    {
        "name": "get_sales_by_period",
        "description": "Obtiene las ventas por período de días. Puede filtrar por producto.",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Número de días hacia atrás (default: 30)"},
                "product_id": {"type": "integer", "description": "ID del producto para filtrar (opcional)"}
            }
        }
    },
    {
        "name": "get_top_selling_products",
        "description": "Obtiene los productos más vendidos en un período.",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Período en días (default: 30)"},
                "limit": {"type": "integer", "description": "Número máximo de productos a retornar (default: 10)"}
            }
        }
    },
    {
        "name": "get_sales_by_category",
        "description": "Obtiene el resumen de ventas agrupado por categoría de producto.",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Período en días (default: 30)"}
            }
        }
    },
    {
        "name": "get_revenue_summary",
        "description": "Obtiene el resumen de ingresos, ganancias brutas y transacciones por período y canal.",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Período en días (default: 30)"}
            }
        }
    },
    {
        "name": "get_product_sales_trend",
        "description": "Obtiene la tendencia de ventas diaria de un producto específico.",
        "input_schema": {
            "type": "object",
            "properties": {
                "product_id": {"type": "integer", "description": "ID del producto"},
                "days": {"type": "integer", "description": "Período en días (default: 30)"}
            },
            "required": ["product_id"]
        }
    },
]


def execute_sales_tool(tool_name: str, tool_input: dict, db_path: str) -> str:
    tool_input["db_path"] = db_path
    dispatch = {
        "get_sales_by_period": get_sales_by_period,
        "get_top_selling_products": get_top_selling_products,
        "get_sales_by_category": get_sales_by_category,
        "get_revenue_summary": get_revenue_summary,
        "get_product_sales_trend": get_product_sales_trend,
    }
    func = dispatch.get(tool_name)
    if not func:
        return json.dumps({"error": f"Herramienta desconocida: {tool_name}"})
    return func(**tool_input)
