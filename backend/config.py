import os
from pathlib import Path
from dotenv import load_dotenv

# Raíz del proyecto = carpeta que contiene a backend/ (este archivo vive en backend/).
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Carga el .env desde la raíz del proyecto sin importar desde dónde se ejecute.
load_dotenv(PROJECT_ROOT / ".env")

# Carpeta persistente para la memoria vectorial (ChromaDB), siempre en la raíz.
VECTOR_STORE_DIR = str(PROJECT_ROOT / "vector_store")

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
