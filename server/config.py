import os
from dotenv import load_dotenv

load_dotenv()  # reads .env if present

ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID", "").strip()
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY", "").strip()

def require_adzuna_keys():
    if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
        raise RuntimeError(
            "Clés Adzuna manquantes. Ajoute ADZUNA_APP_ID et ADZUNA_APP_KEY dans le fichier .env à la racine du projet."
        )