"""Capa de presentación (REST).

Agrupa todos los routers bajo el prefijo /api. Para agregar un endpoint nuevo:
crea/edita un router de dominio en este paquete e inclúyelo aquí.
"""
from fastapi import APIRouter

from . import chat, dashboard, catalog, memory, health

api_router = APIRouter(prefix="/api")
api_router.include_router(chat.router)
api_router.include_router(dashboard.router)
api_router.include_router(catalog.router)
api_router.include_router(memory.router)
api_router.include_router(health.router)

__all__ = ["api_router"]
