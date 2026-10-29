"""Configuration loaded from environment, without embedding credentials."""
import os
from dotenv import load_dotenv

load_dotenv()


def supabase_config() -> tuple[str, str]:
    url = os.getenv("SUPABASE_URL", "").rstrip("/")
    key = os.getenv("SUPABASE_PUBLISHABLE_KEY", "")
    if not url or not key:
        raise RuntimeError("Configurá SUPABASE_URL y SUPABASE_PUBLISHABLE_KEY en el backend.")
    return url, key
