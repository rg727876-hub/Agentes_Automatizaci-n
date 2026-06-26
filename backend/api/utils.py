"""Helpers compartidos por los routers de datos.

Las herramientas de `tools/` devuelven JSON como string. Estos helpers lo
parsean y, sobre todo, son **tolerantes a fallos**: si la BD no responde,
devuelven None en vez de romper todo el endpoint, para que el frontend siga
mostrándose.
"""
import json


def parse_json(raw: str):
    """Parsea el JSON que devuelven las herramientas; None si falla."""
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None


def call_tool(fn, *args):
    """Ejecuta una herramienta de datos y devuelve su JSON parseado (o None)."""
    try:
        return parse_json(fn(*args))
    except Exception as e:  # noqa: BLE001
        print(f"[DATOS] {fn.__name__} falló: {e}")
        return None
