"""Paquete de base de datos (Supabase / PostgreSQL).

Estructura:
  connection.py  -> get_connection() y el wrapper Connection (psycopg2)
  schema.sql     -> definición de tablas (DDL), fuente de verdad
  seed.py        -> datos de ejemplo
  setup.py       -> setup_database(): aplica schema.sql + seed

Se re-exportan get_connection y setup_database para mantener compatibilidad
con `from database import get_connection, setup_database`.
"""
from .connection import get_connection, Connection
from .setup import setup_database

__all__ = ["get_connection", "setup_database", "Connection"]
