from dotenv import dotenv_values
from pathlib import Path
import json
import os

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent

def safe_load_dotenv(path, override=False):
    for key, value in dotenv_values(path).items():
        if value is None:
            continue

        if not override and key in os.environ:
            continue

        # Windows cannot set very large environment variables. Large payloads
        # such as classification JSON are read directly from .env when needed.
        if len(value) > 30000:
            continue

        os.environ[key] = value


safe_load_dotenv(REPO_ROOT / ".env")
safe_load_dotenv(BACKEND_ROOT / ".env", override=True)

class Settings:
    DATABASE_URL = os.getenv("DATABASE_URL")
    DATABASE_SSL = os.getenv("DATABASE_SSL", "true").lower() != "false"
    DATABASE_SSL_REJECT_UNAUTHORIZED = (
        os.getenv("DATABASE_SSL_REJECT_UNAUTHORIZED", "true").lower()
        != "false"
    )
    DATABASE_POOL_MAX = int(os.getenv("DATABASE_POOL_MAX", "10"))

    GOOGLE_OAUTH_CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
    GOOGLE_OAUTH_CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
    GOOGLE_OAUTH_REDIRECT_URI = os.getenv("GOOGLE_OAUTH_REDIRECT_URI")
    FRONTEND_AUTH_REDIRECT_URL = os.getenv("FRONTEND_AUTH_REDIRECT_URL")
    JWT_SECRET = os.getenv("JWT_SECRET") or os.getenv("DASHBOARD_AUTH_TOKEN")
    JWT_EXPIRES_IN_MINUTES = int(os.getenv("JWT_EXPIRES_IN_MINUTES", "10080"))
    TOKEN_ENCRYPTION_SECRET = (
        os.getenv("TOKEN_ENCRYPTION_SECRET")
        or os.getenv("JWT_SECRET")
        or os.getenv("DASHBOARD_AUTH_TOKEN")
    )

    GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
    MAX_GOOGLE_SHEET_SOURCES = int(os.getenv("MAX_GOOGLE_SHEET_SOURCES", "5"))
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
        _raw_registry = json.loads(GOOGLE_SHEET_REGISTRY_JSON)
        SPREADSHEET_REGISTRY = {}
        SPREADSHEET_REGISTRY_META = {}

        for year, value in _raw_registry.items():
            registry_year = str(year).strip()

            if not registry_year:
                continue

            if isinstance(value, dict):
                sheet_id = str(value.get("id", "")).strip()
                sheet_name = str(
                    value.get("name") or f"Google Sheet {registry_year}"
                ).strip()
            else:
                sheet_id = str(value).strip()
                sheet_name = f"Google Sheet {registry_year}"

            if not sheet_id:
                continue

            SPREADSHEET_REGISTRY[registry_year] = sheet_id
            SPREADSHEET_REGISTRY_META[registry_year] = {
                "id": sheet_id,
                "name": sheet_name,
            }
    except json.JSONDecodeError as exc:
        raise ValueError(
            "GOOGLE_SHEET_REGISTRY_JSON harus berupa JSON object valid"
        ) from exc

    if not DASHBOARD_USERNAME:
        raise ValueError("DASHBOARD_USERNAME belum diset di .env")

    if not DASHBOARD_PASSWORD:
        raise ValueError("DASHBOARD_PASSWORD belum diset di .env")

    if not DASHBOARD_AUTH_TOKEN:
        raise ValueError("DASHBOARD_AUTH_TOKEN belum diset di .env")

    if not DATABASE_URL:
        raise ValueError("DATABASE_URL belum diset di .env")

    if not JWT_SECRET:
        raise ValueError("JWT_SECRET atau DASHBOARD_AUTH_TOKEN belum diset di .env")

    if not TOKEN_ENCRYPTION_SECRET:
        raise ValueError(
            "TOKEN_ENCRYPTION_SECRET, JWT_SECRET, atau DASHBOARD_AUTH_TOKEN "
            "belum diset di .env"
        )

    def require_google_oauth_settings(self):
        missing_keys = [
            key
            for key in [
                "GOOGLE_OAUTH_CLIENT_ID",
                "GOOGLE_OAUTH_CLIENT_SECRET",
                "GOOGLE_OAUTH_REDIRECT_URI",
            ]
            if not getattr(self, key)
        ]

        if missing_keys:
            raise ValueError(
                "Google OAuth belum dikonfigurasi: "
                + ", ".join(missing_keys)
            )

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

    def get_sheet_name_for_year(self, year=None):
        if not self.SPREADSHEET_REGISTRY:
            return "Google Sheet"

        selected_year = str(year or self.get_latest_registry_year())
        meta = self.SPREADSHEET_REGISTRY_META.get(selected_year, {})

        return meta.get("name") or f"Google Sheet {selected_year}"

    def get_data_source_for_year(self, year=None):
        selected_year = str(year or self.get_latest_registry_year() or "")

        return {
            "year": selected_year,
            "name": self.get_sheet_name_for_year(selected_year),
        }

settings = Settings()
