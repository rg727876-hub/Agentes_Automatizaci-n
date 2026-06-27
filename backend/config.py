import os
from pathlib import Path
from dotenv import load_dotenv

# Raíz del proyecto = carpeta que contiene a backend/ (este archivo vive en backend/).
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Carga el .env desde la raíz del proyecto sin importar desde dónde se ejecute.
load_dotenv(PROJECT_ROOT / ".env")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# Connection string de Supabase / PostgreSQL.
# Supabase -> Project Settings -> Database -> Connection string (URI).
# Recomendado: el "Session pooler" (compatible con IPv4).
DATABASE_URL = os.environ.get("DATABASE_URL", "")

# Se mantiene por compatibilidad con el resto del código (se pasa entre
# agentes), pero ya no se usa como ruta: la conexión viene de DATABASE_URL.
DB_PATH = "supabase"

ORCHESTRATOR_MODEL = "gemini-3.1-flash-lite"
AGENT_MODEL = "gemini-3.1-flash-lite"

# Temperatura por defecto de los agentes. 0.0 = respuestas deterministas
# (más baratas de cachear y más predecibles para datos de negocio).
LLM_TEMPERATURE = float(os.environ.get("LLM_TEMPERATURE", "0.0"))

# Memoria vectorial (pgvector). Modelo de embeddings de Gemini y su dimensión.
# text-embedding-004 -> 768 dimensiones (debe coincidir con vector(768) en schema.sql).
EMBED_MODEL = "text-embedding-004"
EMBED_DIM = 768

MAX_ITERATIONS = 10
MAX_RETRIES = 2

# Email (opcional — requerido solo para enviar reportes por correo)
EMAIL_SENDER = os.environ.get("EMAIL_SENDER", "")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD", "")
EMAIL_SMTP_SERVER = os.environ.get("EMAIL_SMTP_SERVER", "smtp.gmail.com")
EMAIL_SMTP_PORT = int(os.environ.get("EMAIL_SMTP_PORT", "587"))

# Monitor automático de alertas de inventario
ALERT_EMAIL_TO = os.environ.get("ALERT_EMAIL_TO", EMAIL_SENDER)  # destinatario de alertas
ALERT_CHECK_INTERVAL = int(os.environ.get("ALERT_CHECK_INTERVAL", "60"))  # minutos

# ¿Arrancar el monitor de alertas dentro del servidor web?
# Apagado por defecto: con varias instancias en App Runner enviaría emails
# duplicados. En producción conviene un job externo (ver ARCHITECTURE.md §8).
ENABLE_ALERT_MONITOR = os.environ.get("ENABLE_ALERT_MONITOR", "false").lower() in ("1", "true", "yes")

# ---------------------------------------------------------------------------
# LangSmith (observabilidad: tokens, costo y latencia por traza)
# ---------------------------------------------------------------------------
# Es OPT-IN: sin API key el sistema funciona igual, simplemente no traza.
# Acepta tanto LANGSMITH_API_KEY (nombre nuevo) como LANGCHAIN_API_KEY (clásico).
LANGSMITH_API_KEY = os.environ.get("LANGSMITH_API_KEY", "") or os.environ.get("LANGCHAIN_API_KEY", "")
LANGSMITH_PROJECT = os.environ.get("LANGSMITH_PROJECT", "inventario-retail")


def setup_langsmith() -> bool:
    """Activa el tracing de LangSmith si hay API key. No-op si no la hay.

    Devuelve True si quedó activado. Se llama de forma perezosa al crear el
    primer LLM, así que no rompe nada cuando aún no tienes cuenta de LangSmith.
    """
    if not LANGSMITH_API_KEY:
        return False
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = LANGSMITH_API_KEY
    os.environ["LANGCHAIN_PROJECT"] = LANGSMITH_PROJECT
    return True
