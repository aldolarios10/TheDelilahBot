"""Configuración del bot: lee el archivo .env y define las constantes que usa el resto del código."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# --- Variables del .env ---
TOKEN = os.getenv("TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL")
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "800"))  # tope de tokens por respuesta (cualquier modelo)
HISTORY_LIMIT = int(os.getenv("HISTORY_LIMIT", "10"))  # mensajes anteriores que se mandan a la IA

# --- Constantes ---
TELEGRAM_LIMIT = 4096  # máximo de caracteres por mensaje en Telegram
DRAFT_INTERVAL = 1.0   # segundos mínimos entre borradores (para no saturar a Telegram)
DB_PATH = Path(__file__).parent / "delilah.db"  # la base de datos vive en la raíz del proyecto


def validar():
    """Detiene el bot si falta alguna variable obligatoria. Se llama al arrancar, no al importar."""
    if not TOKEN or not GROQ_API_KEY or not GROQ_MODEL:
        raise SystemExit("Falta TOKEN, GROQ_API_KEY o GROQ_MODEL en el archivo .env")
