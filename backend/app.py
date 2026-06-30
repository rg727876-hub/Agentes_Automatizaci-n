"""Punto de entrada del Sistema Multiagente de Inventario Retail.

Arma la aplicación FastAPI: monta la capa de presentación (routers de `api/`),
gestiona el ciclo de vida (inicialización de BD, memoria y orquestador) y sirve
el frontend estático. Todo corre desde un solo servidor (FastAPI + Uvicorn).

La lógica está repartida por capas (ver ARCHITECTURE.md):
    api/      -> routers REST           agents/  -> orquestador + agentes
    tools/    -> lógica de negocio      memory/  -> memoria vectorial (pgvector)
    database/ -> conexión + esquema

Ejecutar en local (desde la raíz del proyecto o desde backend/):
    python backend/app.py
o bien, con recarga en caliente (estando dentro de backend/):
    uvicorn app:app --reload
"""
import fix_ssl  # debe ser el primer import (configura certificados SSL en Windows)

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from config import PROJECT_ROOT, ALLOWED_ORIGINS, API_KEY, ENABLE_WRITE_TOOLS
from api import api_router
from api.state import lifespan

FRONTEND_DIR = PROJECT_ROOT / "frontend"

app = FastAPI(
    title="Sistema Multiagente de Inventario Retail",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS: solo los orígenes permitidos pueden llamar a la API desde un navegador.
# Si no se configura ALLOWED_ORIGINS, no se habilita CORS cross-origin (el
# frontend se sirve desde el mismo origen, así que no lo necesita).
if ALLOWED_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-API-Key"],
    )

# Avisos de configuración insegura al arrancar (visibles en los logs).
if not API_KEY:
    print("[SEGURIDAD] API_KEY no configurada: la API está ABIERTA (modo desarrollo).")
if ENABLE_WRITE_TOOLS:
    print("[SEGURIDAD] Operaciones de escritura HABILITADAS (los agentes pueden modificar datos).")
else:
    print("[SEGURIDAD] Modo solo-lectura: operaciones de escritura deshabilitadas.")

# Capa de presentación: todos los endpoints REST bajo /api.
app.include_router(api_router)


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

    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("app:app", host="127.0.0.1", port=port, reload=False)
