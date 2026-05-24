from dotenv import load_dotenv
import os

load_dotenv()

class Settings:
    GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
    DASHBOARD_USERNAME = os.getenv("DASHBOARD_USERNAME")
    DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD")
    DASHBOARD_AUTH_TOKEN = os.getenv("DASHBOARD_AUTH_TOKEN")

    if not GOOGLE_SHEET_ID:
        raise ValueError("GOOGLE_SHEET_ID belum diset di .env")

    if not DASHBOARD_USERNAME:
        raise ValueError("DASHBOARD_USERNAME belum diset di .env")

    if not DASHBOARD_PASSWORD:
        raise ValueError("DASHBOARD_PASSWORD belum diset di .env")

    if not DASHBOARD_AUTH_TOKEN:
        raise ValueError("DASHBOARD_AUTH_TOKEN belum diset di .env")

settings = Settings()
