"""Conexión a Supabase / PostgreSQL.

Capa de compatibilidad: permite seguir usando el mismo patrón que sqlite3
(conn.execute(sql, params) con placeholders "?", filas accesibles por índice y
por nombre, conn.executemany / commit / close) pero contra PostgreSQL mediante
psycopg2. La cadena de conexión viene siempre de DATABASE_URL (.env).
"""
import psycopg2
import psycopg2.extras

from config import DATABASE_URL

# psycopg2 devuelve los valores NUMERIC como decimal.Decimal, que json.dumps no
# sabe serializar. Los convertimos a float globalmente (igual que hacía SQLite).
# Esto cubre, por ejemplo, AVG(columna_entera), que en PostgreSQL retorna numeric.
_DEC2FLOAT = psycopg2.extensions.new_type(
    psycopg2.extensions.DECIMAL.values,
    "DEC2FLOAT",
    lambda value, _cur: float(value) if value is not None else None,
)
psycopg2.extensions.register_type(_DEC2FLOAT)


def _translate(sql: str) -> str:
    """Convierte los placeholders estilo SQLite (?) al estilo psycopg2 (%s)."""
    return sql.replace("?", "%s")


class Connection:
    """Envuelve una conexión psycopg2 imitando la API de sqlite3.Connection."""

    def __init__(self, raw):
        self._raw = raw

    def execute(self, sql: str, params=None):
        cur = self._raw.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute(_translate(sql), params)
        return cur

    def executemany(self, sql: str, seq_of_params):
        cur = self._raw.cursor()
        cur.executemany(_translate(sql), seq_of_params)
        return cur

    def executescript(self, sql: str):
        # psycopg2 ejecuta varias sentencias separadas por ';' en un solo execute.
        cur = self._raw.cursor()
        cur.execute(sql)
        return cur

    def commit(self):
        self._raw.commit()

    def close(self):
        self._raw.close()


def get_connection(db_path: str = None) -> Connection:
    """Abre una conexión a Supabase/PostgreSQL usando DATABASE_URL.

    El parámetro db_path se mantiene por compatibilidad con el resto del código
    (que lo pasa de agente en agente) pero se ignora.
    """
    if not DATABASE_URL:
        raise RuntimeError(
            "Falta DATABASE_URL. Configura tu connection string de Supabase en el archivo .env "
            "(Project Settings -> Database -> Connection string)."
        )
    kwargs = {}
    if "sslmode" not in DATABASE_URL:
        kwargs["sslmode"] = "require"
    raw = psycopg2.connect(DATABASE_URL, **kwargs)
    return Connection(raw)
