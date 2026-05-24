from dotenv import load_dotenv
from pathlib import Path
import os

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent

load_dotenv(REPO_ROOT / ".env")
load_dotenv(BACKEND_ROOT / ".env", override=True)

class Settings:
    GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
    DASHBOARD_USERNAME = os.getenv("DASHBOARD_USERNAME")
    DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD")
    DASHBOARD_AUTH_TOKEN = os.getenv("DASHBOARD_AUTH_TOKEN")
    CORS_ALLOWED_ORIGINS = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ALLOWED_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173"
        ).split(",")
        if origin.strip()
    ]

    if not GOOGLE_SHEET_ID:
        raise ValueError("GOOGLE_SHEET_ID belum diset di .env")

    if not DASHBOARD_USERNAME:
        raise ValueError("DASHBOARD_USERNAME belum diset di .env")

    if not DASHBOARD_PASSWORD:
        raise ValueError("DASHBOARD_PASSWORD belum diset di .env")

    if not DASHBOARD_AUTH_TOKEN:
        raise ValueError("DASHBOARD_AUTH_TOKEN belum diset di .env")

settings = Settings()
