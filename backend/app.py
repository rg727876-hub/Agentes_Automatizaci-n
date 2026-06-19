"""Servidor web del Sistema Multiagente de Inventario Retail.

Expone el orquestador de agentes (chat en lenguaje natural) y un conjunto de
endpoints de datos para alimentar el dashboard, además de servir el frontend
estático. Todo corre desde un solo servidor (FastAPI + Uvicorn).

Ejecutar (desde la raíz del proyecto o desde backend/):
    python backend/app.py
o bien:
    uvicorn app:app --reload  (estando dentro de backend/)
"""
import fix_ssl  # debe ser el primer import (configura certificados SSL en Windows)

import json
import threading
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from google import genai

from config import (
    GEMINI_API_KEY,
    DATABASE_URL,
    DB_PATH,
    VECTOR_STORE_DIR,
    PROJECT_ROOT,
)
from database import setup_database, get_connection
from agents import OrchestratorAgent
from memory import VectorMemory

# Herramientas de datos (se llaman directamente para construir el dashboard,
# sin pasar por el LLM — son consultas rápidas a la base de datos).
from tools.inventory_tools import (
    get_inventory_value,
    get_active_alerts,
    get_low_stock_products,
    get_out_of_stock_products,
    get_all_products,
)
from tools.sales_tools import (
    get_revenue_summary,
    get_top_selling_products,
    get_sales_by_category,
    get_sales_by_period,
)
from tools.order_tools import get_pending_orders
from tools.supplier_tools import get_all_suppliers

FRONTEND_DIR = PROJECT_ROOT / "frontend"

# ----------------------------------------------------------------------------
# Estado global del servidor (orquestador + memoria, compartidos)
# ----------------------------------------------------------------------------
_state = {"orchestrator": None, "memory": None, "error": None}
_chat_lock = threading.Lock()  # el orquestador guarda historial de sesión: 1 a la vez


def _load_products_for_index() -> list:
    conn = get_connection(DB_PATH)
    try:
        rows = conn.execute(
            "SELECT p.id, p.sku, p.name, p.category, p.unit_price, i.quantity "
            "FROM products p JOIN inventory i ON p.id = i.product_id"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def _init_system():
    """Inicializa base de datos, memoria vectorial y orquestador una sola vez."""
    if not GEMINI_API_KEY:
        raise RuntimeError("Falta GEMINI_API_KEY en el .env")
    if not DATABASE_URL:
        raise RuntimeError("Falta DATABASE_URL en el .env")

    setup_database(DB_PATH)

    memory = VectorMemory(persist_dir=VECTOR_STORE_DIR)
    memory.index_products(_load_products_for_index())

    client = genai.Client(api_key=GEMINI_API_KEY)
    orchestrator = OrchestratorAgent(client, DB_PATH, memory=memory)

    _state["memory"] = memory
    _state["orchestrator"] = orchestrator


app = FastAPI(title="Sistema Multiagente de Inventario Retail", version="1.0.0")


@app.on_event("startup")
def _on_startup():
    # El arranque no debe tumbar el servidor: si la BD o Gemini fallan, igual
    # servimos el frontend y reportamos el problema en /api/health.
    try:
        _init_system()
        _state["error"] = None
    except Exception as e:  # noqa: BLE001
        _state["error"] = str(e)
        print(f"[ARRANQUE] No se pudo inicializar el sistema: {e}")


# ----------------------------------------------------------------------------
# Modelos de petición
# ----------------------------------------------------------------------------
class ChatRequest(BaseModel):
    message: str


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def _j(raw: str):
    """Parsea el JSON que devuelven las herramientas; vacío si falla."""
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None


def _call(fn, *args):
    """Ejecuta una herramienta de datos y devuelve su JSON parseado.

    Tolerante a fallos: si la BD no responde, devuelve None en vez de romper
    todo el endpoint, para que el frontend siga mostrándose.
    """
    try:
        return _j(fn(*args))
    except Exception as e:  # noqa: BLE001
        print(f"[DATOS] {fn.__name__} falló: {e}")
        return None


# ----------------------------------------------------------------------------
# API — Chat con el orquestador
# ----------------------------------------------------------------------------
@app.post("/api/chat")
def chat(req: ChatRequest):
    message = (req.message or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="El mensaje está vacío.")
    orchestrator = _state["orchestrator"]
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="El sistema aún se está inicializando.")
    with _chat_lock:
        try:
            response = orchestrator.execute(message)
        except Exception as e:  # noqa: BLE001
            raise HTTPException(status_code=500, detail=f"Error del orquestador: {e}")
    return {"response": response}


# ----------------------------------------------------------------------------
# API — Dashboard (KPIs y datos para gráficos)
# ----------------------------------------------------------------------------
@app.get("/api/dashboard")
def dashboard():
    inv = _call(get_inventory_value, DB_PATH) or {}
    revenue = _call(get_revenue_summary, DB_PATH, 30) or {}
    top = _call(get_top_selling_products, DB_PATH, 30, 8) or []
    by_cat = _call(get_sales_by_category, DB_PATH, 30) or []
    daily = _call(get_sales_by_period, DB_PATH, 30) or []
    alerts = _call(get_active_alerts, DB_PATH) or []
    low_stock = _call(get_low_stock_products, DB_PATH) or []
    out_stock = _call(get_out_of_stock_products, DB_PATH) or []
    pending = _call(get_pending_orders, DB_PATH) or {}

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


# ----------------------------------------------------------------------------
# API — Catálogo de productos
# ----------------------------------------------------------------------------
@app.get("/api/products")
def products(category: str | None = None):
    data = _call(get_all_products, DB_PATH, category) or []
    return {"products": data}


@app.get("/api/suppliers")
def suppliers():
    data = _call(get_all_suppliers, DB_PATH) or []
    return {"suppliers": data}


# ----------------------------------------------------------------------------
# API — Memoria (historial y búsqueda semántica)
# ----------------------------------------------------------------------------
@app.get("/api/history")
def history(limit: int = 10):
    memory = _state["memory"]
    if memory is None:
        return {"history": []}
    entries = memory.get_history(limit=limit)
    out = []
    for e in entries:
        agents = _j(e.get("agents_used", "[]")) or []
        out.append({
            "query": e.get("query", ""),
            "timestamp": e.get("timestamp", ""),
            "agents": [a.replace("invoke_", "").replace("_agent", "") for a in agents],
        })
    return {"history": out}


@app.get("/api/search")
def search(q: str):
    memory = _state["memory"]
    if memory is None or not q.strip():
        return {"results": []}
    results = memory.search_products(q.strip(), n_results=8)
    return {"results": results}


@app.get("/api/memory/stats")
def memory_stats():
    memory = _state["memory"]
    if memory is None:
        return {"total_conversations": 0, "total_products_indexed": 0}
    return memory.get_stats()


@app.get("/api/health")
def health():
    return {
        "status": "ok" if _state["orchestrator"] is not None else "error",
        "database": bool(DATABASE_URL),
        "gemini": bool(GEMINI_API_KEY),
        "error": _state["error"],
    }


# ----------------------------------------------------------------------------
# Frontend estático (se monta al final para no pisar las rutas /api)
# ----------------------------------------------------------------------------
if FRONTEND_DIR.exists():
    @app.get("/")
    def index():
        return FileResponse(FRONTEND_DIR / "index.html")

    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
else:
    @app.get("/")
    def index_missing():
        return JSONResponse(
            {"error": "No se encontró la carpeta frontend/.", "esperado_en": str(FRONTEND_DIR)},
            status_code=500,
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=False)
