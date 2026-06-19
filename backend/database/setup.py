"""Inicialización de la base de datos.

setup_database():
  1. Ejecuta el esquema (database/schema.sql) -> crea las tablas si no existen.
  2. Carga los datos de ejemplo (database/seed.py) la primera vez.

Es idempotente: se puede llamar en cada arranque sin duplicar datos.
"""
import os

from .connection import get_connection
from .seed import seed_data

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")


def setup_database(db_path: str = None):
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        schema_sql = f.read()

    conn = get_connection(db_path)
    try:
        conn.executescript(schema_sql)
        conn.commit()
        seed_data(conn)
    finally:
        conn.close()
