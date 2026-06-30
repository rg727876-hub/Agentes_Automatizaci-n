"""Capa de presentación (REST).

Agrupa todos los routers bajo el prefijo /api. Para agregar un endpoint nuevo:
crea/edita un router de dominio en este paquete e inclúyelo aquí.

Seguridad: los routers de datos van protegidos por `require_api_key` (header
`X-API-Key`). `health` queda PÚBLICO para el health check de App Runner. La auth
es opt-in: si `API_KEY` está vacía, no exige nada (modo desarrollo).
"""
from fastapi import APIRouter, Depends

from . import chat, dashboard, catalog, memory, health
from .security import require_api_key

api_router = APIRouter(prefix="/api")

# Protegidos por API key (cuando está configurada).
_protected = [Depends(require_api_key)]
api_router.include_router(chat.router, dependencies=_protected)
api_router.include_router(dashboard.router, dependencies=_protected)
api_router.include_router(catalog.router, dependencies=_protected)
api_router.include_router(memory.router, dependencies=_protected)

# Público: health check (sin credenciales).
api_router.include_router(health.router)

__all__ = ["api_router"]
