import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


os.environ.setdefault("DASHBOARD_USERNAME", "admin")
os.environ.setdefault("DASHBOARD_PASSWORD", "test-password")
os.environ.setdefault("DASHBOARD_AUTH_TOKEN", "static-test-token")
os.environ.setdefault("JWT_SECRET", "jwt-test-secret")
os.environ.setdefault("TOKEN_ENCRYPTION_SECRET", "encrypt-test-secret")

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import app.config as config
from app.config import validate_runtime_environment


LOCAL_URL = "postgresql://postgres:secret@127.0.0.1:5432/finance_dashboard_local"
SUPABASE_URL = "postgresql://postgres:secret@db.project.supabase.co:5432/postgres"
SUPABASE_POOLER_URL = (
    "postgresql://postgres.project:secret@aws-0-ap-southeast-1."
    "pooler.supabase.com:6543/postgres"
)


class RuntimeEnvironmentConfigTestCase(unittest.TestCase):
    def validate(self, app_env, db_target, port, database_url, env_profile=None):
        validate_runtime_environment(
            app_env=app_env,
            env_profile=env_profile or app_env,
            db_target=db_target,
            backend_port=port,
            database_url=database_url,
        )

    def test_local_dev_with_local_postgres_passes(self):
        self.validate("local-dev", "postgres-local", 8000, LOCAL_URL)

    def test_local_dev_with_supabase_fails(self):
        with self.assertRaisesRegex(ValueError, "DB_TARGET=postgres-local"):
            self.validate("local-dev", "supabase", 8000, SUPABASE_URL)

    def test_uat_with_supabase_and_replit_port_passes(self):
        self.validate("uat", "supabase", 3127, SUPABASE_URL)

    def test_uat_with_supabase_migration_url_passes(self):
        migration_url = (
            "postgresql://postgres:secret@db.uatproject.supabase.co:5432/postgres"
        )
        self.validate("uat", "supabase", 3127, migration_url)

    def test_uat_with_supabase_pooler_passes(self):
        self.validate("uat", "supabase", 3127, SUPABASE_POOLER_URL)

    def test_prod_with_supabase_passes(self):
        self.validate("prod", "supabase", 8443, SUPABASE_URL)

    def test_local_prod_with_supabase_passes(self):
        self.validate("local-prod", "supabase", 8001, SUPABASE_URL)

    def test_invalid_environment_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "APP_ENV"):
            self.validate("staging", "supabase", 8000, SUPABASE_URL)

    def test_invalid_environment_profile_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "ENV_PROFILE"):
            self.validate("uat", "supabase", 3127, SUPABASE_URL, "staging")

    def test_local_dev_requires_loopback_database_host(self):
        with self.assertRaisesRegex(ValueError, "PostgreSQL local"):
            self.validate(
                "local-dev",
                "postgres-local",
                8000,
                "postgresql://postgres:secret@remote.example.com:5432/postgres",
            )

    def test_uat_requires_supabase_host(self):
        with self.assertRaisesRegex(ValueError, "database Supabase"):
            self.validate("uat", "supabase", 3127, LOCAL_URL)

    def test_supabase_name_outside_official_host_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "database Supabase"):
            self.validate(
                "uat",
                "supabase",
                3127,
                "postgresql://postgres:secret@supabase.example.com:5432/postgres",
            )

    def test_process_environment_wins_over_dotenv_override(self):
        with TemporaryDirectory() as temp_dir:
            dotenv_path = Path(temp_dir) / ".env.uat"
            dotenv_path.write_text("APP_ENV=local-prod\n", encoding="utf-8")
            with patch.object(config, "PROCESS_ENV_KEYS", frozenset({"APP_ENV"})), patch.dict(
                os.environ, {"APP_ENV": "uat"}, clear=False
            ):
                config.safe_load_dotenv(dotenv_path, override=True)
                self.assertEqual("uat", os.environ["APP_ENV"])


if __name__ == "__main__":
    unittest.main()
