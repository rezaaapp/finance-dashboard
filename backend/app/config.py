from dotenv import dotenv_values
from pathlib import Path
import json
import os
from urllib.parse import unquote, urlparse

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent


def _env_bool(key, default="false"):
    return os.getenv(key, default).strip().lower() in {"1", "true", "yes", "on"}


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


def load_environment_profile():
    profile = os.getenv("ENV_PROFILE") or os.getenv("APP_ENV") or "local-dev"

    if profile not in {"local-dev", "local-prod", "uat", "prod"}:
        return

    safe_load_dotenv(REPO_ROOT / f".env.{profile}", override=True)
    safe_load_dotenv(BACKEND_ROOT / f".env.{profile}", override=True)


SUPPORTED_APP_ENVIRONMENTS = {"local-dev", "local-prod", "uat", "prod"}
SUPABASE_APP_ENVIRONMENTS = {"local-prod", "uat", "prod"}
LOCAL_DATABASE_HOSTS = {"localhost", "127.0.0.1", "::1"}


def validate_runtime_environment(
    *, app_env, env_profile, db_target, backend_port, database_url
):
    if app_env not in SUPPORTED_APP_ENVIRONMENTS:
        supported = ", ".join(sorted(SUPPORTED_APP_ENVIRONMENTS))
        raise ValueError(f"APP_ENV harus salah satu dari: {supported}")

    if env_profile not in SUPPORTED_APP_ENVIRONMENTS:
        supported = ", ".join(sorted(SUPPORTED_APP_ENVIRONMENTS))
        raise ValueError(f"ENV_PROFILE harus salah satu dari: {supported}")

    expected_target = "postgres-local" if app_env == "local-dev" else "supabase"
    if db_target != expected_target:
        raise ValueError(f"{app_env} harus memakai DB_TARGET={expected_target}")

    if app_env == "local-dev" and backend_port != 8000:
        raise ValueError("local-dev default backend port harus 8000")

    if app_env == "local-prod" and backend_port != 8001:
        raise ValueError("local-prod default backend port harus 8001")

    database_host = (urlparse(database_url or "").hostname or "").lower()
    if (
        database_url
        and app_env == "local-dev"
        and database_host not in LOCAL_DATABASE_HOSTS
    ):
        raise ValueError("local-dev harus memakai database PostgreSQL local")

    if (
        database_url
        and app_env in SUPABASE_APP_ENVIRONMENTS
        and "supabase" not in database_host
    ):
        raise ValueError(f"{app_env} harus memakai database Supabase")


safe_load_dotenv(REPO_ROOT / ".env")
safe_load_dotenv(BACKEND_ROOT / ".env", override=True)
load_environment_profile()

class Settings:
    APP_ENV = os.getenv("APP_ENV", "local-dev")
    ENV_PROFILE = os.getenv("ENV_PROFILE", APP_ENV)
    DB_TARGET = os.getenv(
        "DB_TARGET",
        "supabase" if APP_ENV in SUPABASE_APP_ENVIRONMENTS else "postgres-local",
    )
    BACKEND_PORT = int(
        os.getenv(
            "BACKEND_PORT",
            os.getenv("PORT", "8001" if APP_ENV == "local-prod" else "8000"),
        )
    )

    DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DATABASE_URL")
    DATABASE_MIGRATION_URL = (
        os.getenv("DATABASE_MIGRATION_URL")
        or os.getenv("SUPABASE_MIGRATION_DATABASE_URL")
    )
    DATABASE_SSL = os.getenv("DATABASE_SSL", "true").lower() != "false"
    DATABASE_SSL_REJECT_UNAUTHORIZED = (
        os.getenv("DATABASE_SSL_REJECT_UNAUTHORIZED", "true").lower()
        != "false"
    )
    DATABASE_POOL_MAX = int(os.getenv("DATABASE_POOL_MAX", "10"))
    DATABASE_IDLE_TIMEOUT_MS = int(os.getenv("DATABASE_IDLE_TIMEOUT_MS", "30000"))
    DATABASE_CONNECTION_TIMEOUT_MS = int(
        os.getenv("DATABASE_CONNECTION_TIMEOUT_MS", "10000")
    )

    GOOGLE_OAUTH_CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
    GOOGLE_OAUTH_CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
    GOOGLE_OAUTH_REDIRECT_URI = os.getenv(
        "GOOGLE_OAUTH_REDIRECT_URI",
        "http://127.0.0.1:8000/api/google/oauth/callback",
    )
    GOOGLE_LOGIN_REDIRECT_URI = os.getenv(
        "GOOGLE_LOGIN_REDIRECT_URI",
        "http://127.0.0.1:8000/auth/google/callback",
    )
    GOOGLE_OAUTH_SCOPES = os.getenv(
        "GOOGLE_OAUTH_SCOPES",
        "openid email profile https://www.googleapis.com/auth/spreadsheets",
    )
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://127.0.0.1:5173")
    FRONTEND_AUTH_REDIRECT_URL = os.getenv("FRONTEND_AUTH_REDIRECT_URL")
    JWT_SECRET = os.getenv("JWT_SECRET") or os.getenv("DASHBOARD_AUTH_TOKEN")
    JWT_EXPIRES_IN_MINUTES = int(os.getenv("JWT_EXPIRES_IN_MINUTES", "10080"))
    TOKEN_ENCRYPTION_KEY = os.getenv("TOKEN_ENCRYPTION_KEY")
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
    SUPER_ADMIN_EMAILS = [
        email.strip().lower()
        for email in os.getenv("SUPER_ADMIN_EMAILS", "").split(",")
        if email.strip()
    ]
    USE_MOCK_DATA = os.getenv("USE_MOCK_DATA", "false").lower() == "true"
    AI_CLASSIFICATION_ENABLED = _env_bool("AI_CLASSIFICATION_ENABLED", "false")
    AI_PROVIDER = os.getenv("AI_PROVIDER", "rule_based")
    AI_MODEL = os.getenv("AI_MODEL", "none")
    AI_ONLY_LOW_CONFIDENCE = _env_bool("AI_ONLY_LOW_CONFIDENCE", "true")
    AI_CONFIDENCE_THRESHOLD = float(os.getenv("AI_CONFIDENCE_THRESHOLD", "0.75"))
    AI_MAX_TRANSACTIONS_PER_RUN = int(
        os.getenv("AI_MAX_TRANSACTIONS_PER_RUN", "500")
    )
    INSIGHT_NEED_WARNING_RATIO = float(
        os.getenv("INSIGHT_NEED_WARNING_RATIO", "0.80")
    )
    INSIGHT_NEED_DANGER_RATIO = float(
        os.getenv("INSIGHT_NEED_DANGER_RATIO", "0.90")
    )
    INSIGHT_WANT_WARNING_RATIO = float(
        os.getenv("INSIGHT_WANT_WARNING_RATIO", "0.30")
    )
    INSIGHT_WANT_DANGER_RATIO = float(
        os.getenv("INSIGHT_WANT_DANGER_RATIO", "0.45")
    )
    INSIGHT_SAVING_WARNING_RATIO = float(
        os.getenv("INSIGHT_SAVING_WARNING_RATIO", "0.10")
    )
    INSIGHT_SAVING_GOOD_RATIO = float(
        os.getenv("INSIGHT_SAVING_GOOD_RATIO", "0.20")
    )
    INSIGHT_UNCATEGORIZED_WARNING_COUNT = int(
        os.getenv("INSIGHT_UNCATEGORIZED_WARNING_COUNT", "1")
    )
    INSIGHT_UNCATEGORIZED_DANGER_COUNT = int(
        os.getenv("INSIGHT_UNCATEGORIZED_DANGER_COUNT", "20")
    )
    INSIGHT_ANOMALY_WARNING_MULTIPLIER = float(
        os.getenv("INSIGHT_ANOMALY_WARNING_MULTIPLIER", "2.0")
    )
    INSIGHT_ANOMALY_DANGER_MULTIPLIER = float(
        os.getenv("INSIGHT_ANOMALY_DANGER_MULTIPLIER", "3.0")
    )
    CORS_ALLOWED_ORIGINS = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ALLOWED_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173"
        ).split(",")
        if origin.strip()
    ]
    IMPORT_TEMP_DIR = os.getenv(
        "IMPORT_TEMP_DIR",
        str(BACKEND_ROOT / "output" / "imports" / "temp" / APP_ENV),
    )

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

    if not JWT_SECRET:
        raise ValueError("JWT_SECRET atau DASHBOARD_AUTH_TOKEN belum diset di .env")

    if not TOKEN_ENCRYPTION_SECRET:
        raise ValueError(
            "TOKEN_ENCRYPTION_SECRET, JWT_SECRET, atau DASHBOARD_AUTH_TOKEN "
            "belum diset di .env"
        )

    validate_runtime_environment(
        app_env=APP_ENV,
        env_profile=ENV_PROFILE,
        db_target=DB_TARGET,
        backend_port=BACKEND_PORT,
        database_url=DATABASE_URL,
    )

    def get_database_summary(self):
        parsed = urlparse(self.DATABASE_URL or "")
        host = parsed.hostname or ""
        database_name = unquote(parsed.path.lstrip("/")) if parsed.path else ""

        return {
            "host": self._mask_host(host),
            "database": database_name or "(not configured)",
        }

    def get_startup_summary(self):
        database = self.get_database_summary()

        return {
            "APP_ENV": self.APP_ENV,
            "ENV_PROFILE": self.ENV_PROFILE,
            "DB_TARGET": self.DB_TARGET,
            "backend_port": self.BACKEND_PORT,
            "database_host": database["host"],
            "database_name": database["database"],
            "cors_origins": self.CORS_ALLOWED_ORIGINS,
            "frontend_url": self.FRONTEND_URL,
            "import_temp_dir": self.IMPORT_TEMP_DIR,
        }

    @staticmethod
    def _mask_host(host):
        if not host:
            return "(not configured)"

        if host in {"localhost", "127.0.0.1", "::1"}:
            return host

        parts = host.split(".")

        if len(parts) >= 3:
            return f"{parts[0][:2]}***.{'.'.join(parts[-2:])}"

        if len(host) <= 4:
            return "***"

        return f"{host[:2]}***{host[-2:]}"

    def require_google_oauth_settings(self):
        missing_keys = [
            key
            for key in [
                "GOOGLE_OAUTH_CLIENT_ID",
                "GOOGLE_OAUTH_CLIENT_SECRET",
                "GOOGLE_OAUTH_REDIRECT_URI",
                "GOOGLE_OAUTH_SCOPES",
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

    def get_default_insight_settings(self):
        return {
            "need_warning_ratio": self.INSIGHT_NEED_WARNING_RATIO,
            "need_danger_ratio": self.INSIGHT_NEED_DANGER_RATIO,
            "want_warning_ratio": self.INSIGHT_WANT_WARNING_RATIO,
            "want_danger_ratio": self.INSIGHT_WANT_DANGER_RATIO,
            "saving_warning_ratio": self.INSIGHT_SAVING_WARNING_RATIO,
            "saving_good_ratio": self.INSIGHT_SAVING_GOOD_RATIO,
            "uncategorized_warning_count": self.INSIGHT_UNCATEGORIZED_WARNING_COUNT,
            "uncategorized_danger_count": self.INSIGHT_UNCATEGORIZED_DANGER_COUNT,
            "anomaly_warning_multiplier": self.INSIGHT_ANOMALY_WARNING_MULTIPLIER,
            "anomaly_danger_multiplier": self.INSIGHT_ANOMALY_DANGER_MULTIPLIER,
        }

settings = Settings()
