import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


os.environ.setdefault("DASHBOARD_USERNAME", "admin")
os.environ.setdefault("DASHBOARD_PASSWORD", "test-password")
os.environ.setdefault("DASHBOARD_AUTH_TOKEN", "static-test-token")
os.environ.setdefault("JWT_SECRET", "jwt-test-secret")
os.environ.setdefault("TOKEN_ENCRYPTION_SECRET", "encrypt-test-secret")

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.main import system_info


class SystemInfoTestCase(unittest.TestCase):
    def test_system_info_exposes_only_safe_environment_metadata(self):
        migration = {
            "table_found": True,
            "count": 24,
            "latest": "021_backfill_blu_transaction_search_index.sql",
        }
        database = {
            "host": "aw***.supabase.com",
            "database": "postgres",
        }

        with patch("app.main.settings.APP_ENV", "uat"), patch(
            "app.main.settings.ENV_PROFILE", "uat"
        ), patch("app.main.settings.DB_TARGET", "supabase"), patch(
            "app.main.settings.BACKEND_PORT", 3127
        ), patch(
            "app.main.settings.IMPORT_TEMP_DIR",
            "backend/output/imports/temp/uat",
        ), patch(
            "app.main.settings.get_database_summary", return_value=database
        ), patch(
            "app.main.get_migration_status", return_value=migration
        ):
            payload = system_info()

        self.assertEqual("uat", payload["app_env"])
        self.assertEqual("uat", payload["env_profile"])
        self.assertEqual(3127, payload["backend_port"])
        self.assertEqual("supabase", payload["db_target"])
        self.assertEqual("aw***.supabase.com", payload["database_host"])
        self.assertEqual(24, payload["migration_count"])
        self.assertEqual(migration["latest"], payload["latest_migration"])
        self.assertFalse(
            {
                "database_url",
                "password",
                "token",
                "jwt_secret",
                "oauth_secret",
            }
            & set(payload)
        )


if __name__ == "__main__":
    unittest.main()
