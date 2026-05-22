import json
from datetime import datetime, timedelta
from database import get_connection


def calculate_average_daily_sales(db_path: str, product_id: int, days: int = 30) -> str:
    conn = get_connection(db_path)
    try:
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        result = conn.execute(
            "SELECT p.name, p.sku, SUM(s.quantity) as total_sold, "
            "CAST(SUM(s.quantity) AS REAL) / ? as avg_daily_sales "
            "FROM sales s JOIN products p ON s.product_id = p.id "
            "WHERE s.product_id = ? AND s.sale_date >= ?",
            (days, product_id, start_date)
        ).fetchone()
        if not result or result[0] is None:
            return json.dumps({"error": "No hay datos de ventas para este producto"})
        return json.dumps({
            "product_name": result[0],
            "sku": result[1],
            "period_days": days,
            "total_sold": result[2] or 0,
            "avg_daily_sales": round(result[3] or 0, 2)
        }, ensure_ascii=False)
    finally:
        conn.close()


def forecast_demand(db_path: str, product_id: int, forecast_days: int = 30) -> str:
    conn = get_connection(db_path)
    try:
        recent = conn.execute(
            "SELECT CAST(SUM(quantity) AS REAL) / 30 as avg_30d FROM sales "
            "WHERE product_id = ? AND sale_date >= ?",
            (product_id, (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"))
        ).fetchone()
        older = conn.execute(
            "SELECT CAST(SUM(quantity) AS REAL) / 30 as avg_prev_30d FROM sales "
            "WHERE product_id = ? AND sale_date >= ? AND sale_date < ?",
            (
                product_id,
                (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d"),
                (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            )
        ).fetchone()
        product = conn.execute("SELECT name, sku FROM products WHERE id = ?", (product_id,)).fetchone()
        if not product:
            return json.dumps({"error": "Producto no encontrado"})

        avg_recent = recent[0] or 0
        avg_older = older[0] or 0
        trend_factor = 1.0
        if avg_older > 0:
            trend_factor = avg_recent / avg_older

        forecasted_qty = round(avg_recent * forecast_days * trend_factor)
        return json.dumps({
            "product_name": product[0],
            "sku": product[1],
            "forecast_days": forecast_days,
            "avg_daily_sales_recent_30d": round(avg_recent, 2),
            "avg_daily_sales_prev_30d": round(avg_older, 2),
            "trend_factor": round(trend_factor, 3),
            "forecasted_demand": forecasted_qty,
            "forecasted_daily_avg": round(avg_recent * trend_factor, 2)
        }, ensure_ascii=False)
    finally:
        conn.close()


def calculate_days_of_stock_remaining(db_path: str, product_id: int = None) -> str:
    conn = get_connection(db_path)
    try:
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        if product_id:
            rows = conn.execute(
                "SELECT p.id, p.sku, p.name, i.quantity as current_stock, "
                "COALESCE(CAST(SUM(s.quantity) AS REAL) / 30, 0) as avg_daily_sales, "
                "CASE WHEN COALESCE(CAST(SUM(s.quantity) AS REAL) / 30, 0) > 0 "
                "THEN CAST(i.quantity AS REAL) / (CAST(SUM(s.quantity) AS REAL) / 30) "
                "ELSE 999 END as days_remaining "
                "FROM products p JOIN inventory i ON p.id = i.product_id "
                "LEFT JOIN sales s ON p.id = s.product_id AND s.sale_date >= ? "
                "WHERE p.id = ? GROUP BY p.id",
                (start_date, product_id)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT p.id, p.sku, p.name, i.quantity as current_stock, "
                "COALESCE(CAST(SUM(s.quantity) AS REAL) / 30, 0) as avg_daily_sales, "
                "CASE WHEN COALESCE(CAST(SUM(s.quantity) AS REAL) / 30, 0) > 0 "
                "THEN CAST(i.quantity AS REAL) / (CAST(SUM(s.quantity) AS REAL) / 30) "
                "ELSE 999 END as days_remaining "
                "FROM products p JOIN inventory i ON p.id = i.product_id "
                "LEFT JOIN sales s ON p.id = s.product_id AND s.sale_date >= ? "
                "GROUP BY p.id ORDER BY days_remaining ASC",
                (start_date,)
            ).fetchall()
        return json.dumps([{
            "id": r[0], "sku": r[1], "name": r[2],
            "current_stock": r[3],
            "avg_daily_sales": round(r[4], 2),
            "days_remaining": round(r[5], 1)
        } for r in rows], ensure_ascii=False)
    finally:
        conn.close()


def identify_stockout_risk(db_path: str, risk_days: int = 14) -> str:
    conn = get_connection(db_path)
    try:
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        rows = conn.execute(
            "SELECT p.id, p.sku, p.name, p.category, i.quantity as current_stock, "
            "p.reorder_point, p.reorder_quantity, "
            "COALESCE(CAST(SUM(s.quantity) AS REAL) / 30, 0) as avg_daily_sales, "
            "CASE WHEN COALESCE(CAST(SUM(s.quantity) AS REAL) / 30, 0) > 0 "
            "THEN CAST(i.quantity AS REAL) / (CAST(SUM(s.quantity) AS REAL) / 30) "
            "ELSE 999 END as days_remaining "
            "FROM products p JOIN inventory i ON p.id = i.product_id "
            "LEFT JOIN sales s ON p.id = s.product_id AND s.sale_date >= ? "
            "GROUP BY p.id "
            "HAVING days_remaining <= ? OR current_stock = 0 "
            "ORDER BY days_remaining ASC",
            (start_date, risk_days)
        ).fetchall()
        result = []
        for r in rows:
            risk_level = "CRITICO" if r[4] == 0 or r[5] <= 3 else "ALTO" if r[5] <= 7 else "MEDIO"
            result.append({
                "id": r[0], "sku": r[1], "name": r[2], "category": r[3],
                "current_stock": r[4], "reorder_point": r[5], "reorder_quantity": r[6],
                "avg_daily_sales": round(r[7], 2), "days_remaining": round(r[8], 1),
                "risk_level": risk_level
            })
        return json.dumps(result, ensure_ascii=False)
    finally:
        conn.close()


def get_seasonal_analysis(db_path: str, product_id: int) -> str:
    conn = get_connection(db_path)
    try:
        product = conn.execute("SELECT name, sku FROM products WHERE id = ?", (product_id,)).fetchone()
        if not product:
            return json.dumps({"error": "Producto no encontrado"})
        weekly = conn.execute(
            "SELECT strftime('%W', sale_date) as week_number, "
            "SUM(quantity) as weekly_sales, AVG(quantity) as avg_daily "
            "FROM sales WHERE product_id = ? "
            "GROUP BY week_number ORDER BY week_number",
            (product_id,)
        ).fetchall()
        return json.dumps({
            "product_name": product[0],
            "sku": product[1],
            "weekly_breakdown": [dict(r) for r in weekly]
        }, ensure_ascii=False)
    finally:
        conn.close()


DEMAND_TOOLS = [
    {
        "name": "calculate_average_daily_sales",
        "description": "Calcula el promedio de ventas diarias de un producto en un período dado.",
        "input_schema": {
            "type": "object",
            "properties": {
                "product_id": {"type": "integer", "description": "ID del producto"},
                "days": {"type": "integer", "description": "Período de análisis en días (default: 30)"}
            },
            "required": ["product_id"]
        }
    },
    {
        "name": "forecast_demand",
        "description": "Pronostica la demanda futura de un producto basado en tendencias de ventas.",
        "input_schema": {
            "type": "object",
            "properties": {
                "product_id": {"type": "integer", "description": "ID del producto"},
                "forecast_days": {"type": "integer", "description": "Días a pronosticar (default: 30)"}
            },
            "required": ["product_id"]
        }
    },
    {
        "name": "calculate_days_of_stock_remaining",
        "description": "Calcula cuántos días de stock quedan para un producto o todos los productos.",
        "input_schema": {
            "type": "object",
            "properties": {
                "product_id": {"type": "integer", "description": "ID del producto (opcional, si se omite analiza todos)"}
            }
        }
    },
    {
        "name": "identify_stockout_risk",
        "description": "Identifica productos en riesgo de quedar sin stock en los próximos N días.",
        "input_schema": {
            "type": "object",
            "properties": {
                "risk_days": {"type": "integer", "description": "Ventana de días para identificar riesgo (default: 14)"}
            }
        }
    },
    {
        "name": "get_seasonal_analysis",
        "description": "Analiza patrones de ventas semanales de un producto para identificar estacionalidad.",
        "input_schema": {
            "type": "object",
            "properties": {
                "product_id": {"type": "integer", "description": "ID del producto"}
            },
            "required": ["product_id"]
        }
    },
]


def execute_demand_tool(tool_name: str, tool_input: dict, db_path: str) -> str:
    tool_input["db_path"] = db_path
    dispatch = {
        "calculate_average_daily_sales": calculate_average_daily_sales,
        "forecast_demand": forecast_demand,
        "calculate_days_of_stock_remaining": calculate_days_of_stock_remaining,
        "identify_stockout_risk": identify_stockout_risk,
        "get_seasonal_analysis": get_seasonal_analysis,
    }
    func = dispatch.get(tool_name)
    if not func:
        return json.dumps({"error": f"Herramienta desconocida: {tool_name}"})
    return func(**tool_input)
