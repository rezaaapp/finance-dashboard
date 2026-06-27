import unittest
from unittest.mock import patch

from backend.scripts.database_lifecycle import (
    LOCAL_DATABASE,
    SUPABASE_MIGRATE_PHRASE,
    SUPABASE_RESET_PHRASE,
    parse_database_target,
    validate_environment,
    verify_database_connection,
)


def environment_for(target):
    if target == "local-dev":
        return {
            "APP_ENV": "local-dev",
            "ENV_PROFILE": "local-dev",
            "DB_TARGET": "postgres-local",
            "DATABASE_URL": (
                "postgresql://postgres:secret@127.0.0.1:5432/"
                f"{LOCAL_DATABASE}"
            ),
        }
    return {
        "APP_ENV": "local-prod",
        "ENV_PROFILE": "local-prod",
        "DB_TARGET": "supabase",
        "DATABASE_SSL": "true",
        "DATABASE_SSL_REJECT_UNAUTHORIZED": "true",
        "DATABASE_URL": "postgresql://postgres:secret@db.project.supabase.co:5432/postgres",
    }


class DatabaseLifecycleGuardTestCase(unittest.TestCase):
    def test_local_prod_rejects_localhost(self):
        with self.assertRaisesRegex(ValueError, "loopback"):
            parse_database_target(
                "postgresql://postgres:secret@localhost:5432/postgres", "local-prod"
            )

    def test_local_dev_rejects_supabase(self):
        with self.assertRaisesRegex(ValueError, "Supabase"):
            parse_database_target(
                "postgresql://postgres:secret@db.project.supabase.co:5432/"
                f"{LOCAL_DATABASE}",
                "local-dev",
            )

    def test_supabase_reset_requires_confirmation_phrase(self):
        with self.assertRaisesRegex(ValueError, SUPABASE_RESET_PHRASE):
            validate_environment(environment_for("local-prod"), "local-prod", "reset")

    def test_supabase_migration_requires_confirmation_phrase(self):
        with self.assertRaisesRegex(ValueError, SUPABASE_MIGRATE_PHRASE):
            validate_environment(environment_for("local-prod"), "local-prod", "migrate")

    def test_supabase_confirmation_phrases_are_accepted(self):
        for action, phrase in (
            ("reset", SUPABASE_RESET_PHRASE),
            ("migrate", SUPABASE_MIGRATE_PHRASE),
        ):
            with self.subTest(action=action):
                selected, _, parsed = validate_environment(
                    environment_for("local-prod"), "local-prod", action, phrase
                )
                self.assertEqual("DATABASE_URL", selected)
                self.assertIn("supabase", parsed.hostname)

    def test_wrong_identity_and_db_target_are_rejected(self):
        for key, value in (
            ("APP_ENV", "local-prod"),
            ("ENV_PROFILE", "local-prod"),
            ("DB_TARGET", "supabase"),
        ):
            with self.subTest(key=key):
                environment = environment_for("local-dev")
                environment[key] = value
                with self.assertRaisesRegex(ValueError, key):
                    validate_environment(environment, "local-dev", "verify")

    def test_migration_url_is_preferred_and_validated(self):
        environment = environment_for("local-dev")
        environment["DATABASE_MIGRATION_URL"] = (
            "postgresql://postgres:secret@localhost:5432/" f"{LOCAL_DATABASE}"
        )
        selected, _, parsed = validate_environment(environment, "local-dev", "migrate")
        self.assertEqual("DATABASE_MIGRATION_URL", selected)
        self.assertEqual("localhost", parsed.hostname)

    def test_connection_verification_uses_runtime_database_url(self):
        environment = environment_for("local-dev")
        environment["DATABASE_MIGRATION_URL"] = (
            "postgresql://postgres:secret@localhost:5432/" f"{LOCAL_DATABASE}"
        )
        selected, _, parsed = validate_environment(
            environment, "local-dev", "connection"
        )
        self.assertEqual("DATABASE_URL", selected)
        self.assertEqual("127.0.0.1", parsed.hostname)

    def test_local_prod_connection_requires_ssl_env(self):
        environment = environment_for("local-prod")
        environment["DATABASE_SSL"] = "false"
        with self.assertRaisesRegex(ValueError, "DATABASE_SSL must be true"):
            validate_environment(environment, "local-prod", "connection")


class FakeCursor:
    def __init__(self, ssl_active=True):
        self.ssl_active = ssl_active
        self.executed = []
        self.last_query = ""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, query):
        self.last_query = " ".join(query.lower().split())
        self.executed.append(self.last_query)

    def fetchone(self):
        if self.last_query == "set transaction read only":
            raise AssertionError("SET TRANSACTION does not return a row")
        if self.last_query == "show transaction_read_only":
            return ("on",)
        if self.last_query == "select 1":
            return (1,)
        if "to_regclass" in self.last_query:
            return ("schema_migrations",)
        if "count(*)" in self.last_query:
            return (22, "021_backfill_blu_transaction_search_index.sql")
        raise AssertionError(f"Unexpected query: {self.last_query}")


class FakeConnection:
    def __init__(self, ssl_active=True):
        self.cursor_instance = FakeCursor(ssl_active=ssl_active)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def cursor(self):
        return self.cursor_instance

    def transaction(self, force_rollback=False):
        if not force_rollback:
            raise AssertionError("Connection verification must force rollback")
        return self


class ConnectionVerificationTestCase(unittest.TestCase):
    def test_verification_is_read_only_and_reports_migrations(self):
        connection = FakeConnection()
        with patch.dict(
            "backend.scripts.database_lifecycle.os.environ",
            {"DATABASE_SSL_REJECT_UNAUTHORIZED": "true"},
        ):
            with patch(
                "backend.scripts.database_lifecycle.psycopg.connect",
                return_value=connection,
            ) as connect:
                result = verify_database_connection(
                    "postgresql://postgres:secret@db.project.supabase.co:5432/postgres",
                    "local-prod",
                )

        connect.assert_called_once_with(
            "postgresql://postgres:secret@db.project.supabase.co:5432/postgres",
            sslmode="verify-full",
        )
        self.assertTrue(result["ssl_active"])
        self.assertEqual(22, result["migration_count"])
        self.assertEqual(
            "021_backfill_blu_transaction_search_index.sql",
            result["latest_migration"],
        )
        self.assertTrue(
            all(
                query.startswith(("select ", "set transaction read only", "show "))
                for query in connection.cursor_instance.executed
            )
        )

    def test_local_prod_forces_ssl(self):
        with patch.dict(
            "backend.scripts.database_lifecycle.os.environ",
            {"DATABASE_SSL_REJECT_UNAUTHORIZED": "true"},
        ):
            with patch(
                "backend.scripts.database_lifecycle.psycopg.connect",
                return_value=FakeConnection(),
            ) as connect:
                verify_database_connection(
                    "postgresql://postgres:secret@db.project.supabase.co:5432/postgres",
                    "local-prod",
                )
        self.assertEqual("verify-full", connect.call_args.kwargs["sslmode"])


if __name__ == "__main__":
    unittest.main()
