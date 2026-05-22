import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
DB_PATH = "inventory.db"
ORCHESTRATOR_MODEL = "gemini-2.5-flash-lite"
AGENT_MODEL = "gemini-2.5-flash-lite"
MAX_ITERATIONS = 10
MAX_RETRIES = 3
