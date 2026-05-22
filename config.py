import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
DB_PATH = "inventory.db"

ORCHESTRATOR_MODEL = "gemini-3.1-flash-lite"
AGENT_MODEL = "gemini-3.1-flash-lite"

MAX_ITERATIONS = 10
MAX_RETRIES = 2

# Email (opcional — requerido solo para enviar reportes por correo)
EMAIL_SENDER = os.environ.get("EMAIL_SENDER", "")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD", "")
EMAIL_SMTP_SERVER = os.environ.get("EMAIL_SMTP_SERVER", "smtp.gmail.com")
EMAIL_SMTP_PORT = int(os.environ.get("EMAIL_SMTP_PORT", "587"))
