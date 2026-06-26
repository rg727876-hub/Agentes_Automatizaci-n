# ============================================================================
#  Imagen para AWS App Runner (y cualquier runtime de contenedores)
#  Un solo servicio: FastAPI (Uvicorn) que sirve la API y el frontend.
# ============================================================================
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 1) Dependencias primero (mejor caché de capas).
#    psycopg2-binary trae sus propios wheels: no requiere libpq-dev.
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --upgrade pip && pip install -r backend/requirements.txt

# 2) Código de la aplicación.
#    config.py calcula PROJECT_ROOT = parent.parent de backend/, es decir /app,
#    por eso copiamos backend/ y frontend/ manteniendo esa estructura.
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# Los imports son planos (raíz = backend/), así que ejecutamos desde ahí.
WORKDIR /app/backend

# App Runner enruta el tráfico al puerto configurado (usaremos 8000).
EXPOSE 8000

# App Runner puede inyectar PORT; si no, usamos 8000.
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}"]
