"""Autenticación de la API por clave (header `X-API-Key`).

Es **opt-in**: si `API_KEY` está vacía en la configuración, la auth queda
desactivada (modo desarrollo) y se imprime una advertencia al arrancar. Cuando
defines `API_KEY`, todos los endpoints protegidos exigen el header
`X-API-Key: <tu-clave>` y devuelven 401 si falta o no coincide.

El endpoint `/api/health` se deja PÚBLICO a propósito: App Runner lo usa como
health check y no debe requerir credenciales.

> Nota: para una app con frontend en el navegador, exponer la API key en el
> cliente es débil (queda visible). Esto protege el acceso programático y sirve
> de compuerta básica; el siguiente paso natural es un login con JWT por usuario
> (ver ARCHITECTURE.md §9).
"""
import hmac

from fastapi import Header, HTTPException, status

from config import API_KEY


def require_api_key(x_api_key: str = Header(default="", alias="X-API-Key")) -> None:
    """Dependencia FastAPI: valida el header X-API-Key contra la clave configurada."""
    # Sin clave configurada → auth desactivada (no rompe el uso local).
    if not API_KEY:
        return
    # Comparación en tiempo constante para no filtrar info por timing.
    if not x_api_key or not hmac.compare_digest(x_api_key, API_KEY):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Falta o es inválida la cabecera X-API-Key.",
        )
