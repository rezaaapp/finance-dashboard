from dotenv import load_dotenv
from pathlib import Path
import json
import os

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent

load_dotenv(REPO_ROOT / ".env")
load_dotenv(BACKEND_ROOT / ".env", override=True)

class Settings:
    GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
    GOOGLE_SHEET_REGISTRY_JSON = os.getenv("GOOGLE_SHEET_REGISTRY_JSON", "{}")
    DASHBOARD_USERNAME = os.getenv("DASHBOARD_USERNAME")
    DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD")
    DASHBOARD_AUTH_TOKEN = os.getenv("DASHBOARD_AUTH_TOKEN")
    USE_MOCK_DATA = os.getenv("USE_MOCK_DATA", "false").lower() == "true"
    CORS_ALLOWED_ORIGINS = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ALLOWED_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173"
        ).split(",")
        if origin.strip()
    ]

    try:
        SPREADSHEET_REGISTRY = {
            str(year): sheet_id
            for year, sheet_id in json.loads(GOOGLE_SHEET_REGISTRY_JSON).items()
            if str(year).strip() and str(sheet_id).strip()
        }
    except json.JSONDecodeError as exc:
        raise ValueError(
            "GOOGLE_SHEET_REGISTRY_JSON harus berupa JSON object valid"
        ) from exc

    if not GOOGLE_SHEET_ID and not SPREADSHEET_REGISTRY:
        raise ValueError(
            "GOOGLE_SHEET_ID atau GOOGLE_SHEET_REGISTRY_JSON belum diset di .env"
        )

    if not DASHBOARD_USERNAME:
        raise ValueError("DASHBOARD_USERNAME belum diset di .env")

    if not DASHBOARD_PASSWORD:
        raise ValueError("DASHBOARD_PASSWORD belum diset di .env")

    if not DASHBOARD_AUTH_TOKEN:
        raise ValueError("DASHBOARD_AUTH_TOKEN belum diset di .env")

    def get_available_registry_years(self):
        return sorted(
            [int(year) for year in self.SPREADSHEET_REGISTRY.keys()],
            reverse=True
        )

    def get_latest_registry_year(self):
        years = self.get_available_registry_years()

        return str(years[0]) if years else None

    def get_sheet_id_for_year(self, year=None):
        if not self.SPREADSHEET_REGISTRY:
            return self.GOOGLE_SHEET_ID

        selected_year = str(year or self.get_latest_registry_year())
        sheet_id = self.SPREADSHEET_REGISTRY.get(selected_year)

        if not sheet_id:
            available_years = ", ".join(self.SPREADSHEET_REGISTRY.keys())
            raise ValueError(
                f"Spreadsheet untuk tahun {selected_year} tidak ditemukan. "
                f"Tahun tersedia: {available_years}"
            )

        return sheet_id

settings = Settings()
