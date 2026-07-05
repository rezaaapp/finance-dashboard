import os
import sys
import unittest
from pathlib import Path


os.environ.setdefault("DASHBOARD_USERNAME", "admin")
os.environ.setdefault("DASHBOARD_PASSWORD", "test-password")
os.environ.setdefault("DASHBOARD_AUTH_TOKEN", "static-test-token")
os.environ.setdefault("JWT_SECRET", "jwt-test-secret")
os.environ.setdefault("TOKEN_ENCRYPTION_SECRET", "encrypt-test-secret")

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.config import validate_runtime_environment


LOCAL_URL = "postgresql://postgres:secret@127.0.0.1:5432/finance_dashboard_local"
SUPABASE_URL = "postgresql://postgres:secret@db.project.supabase.co:5432/postgres"


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

    def test_prod_with_supabase_passes(self):
        self.validate("prod", "supabase", 8443, SUPABASE_URL)

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


if __name__ == "__main__":
    unittest.main()
