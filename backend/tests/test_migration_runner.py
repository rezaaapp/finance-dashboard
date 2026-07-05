import tempfile
import unittest
from pathlib import Path

from backend.scripts.run_migrations import apply_migration, select_migration_database_url


class FakeTransaction:
    def __init__(self, connection):
        self.connection = connection

    def __enter__(self):
        self.connection.transaction_entries += 1
        return self

    def __exit__(self, exc_type, exc, tb):
        self.connection.transaction_exits.append(exc_type)
        return False


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection
        self.last_select_applied = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=None):
        self.connection.executed.append((sql, params))

        if "select 1 from schema_migrations" in sql.lower():
            self.last_select_applied = self.connection.already_applied
            return

        if sql == self.connection.migration_sql and self.connection.fail_on_migration_sql:
            raise RuntimeError("migration exploded")

    def fetchone(self):
        if self.last_select_applied:
            return (1,)
        return None


class FakeConnection:
    def __init__(self, *, migration_sql, already_applied=False, fail_on_migration_sql=False):
        self.migration_sql = migration_sql
        self.already_applied = already_applied
        self.fail_on_migration_sql = fail_on_migration_sql
        self.executed = []
        self.transaction_entries = 0
        self.transaction_exits = []

    def transaction(self):
        return FakeTransaction(self)

    def cursor(self):
        return FakeCursor(self)


class MigrationRunnerTestCase(unittest.TestCase):
    def create_migration_file(self, contents: str) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        migration_path = Path(temp_dir.name) / "999_test_migration.sql"
        migration_path.write_text(contents, encoding="utf-8")
        return migration_path

    def test_apply_migration_runs_sql_and_records_version_in_single_transaction(self):
        migration_sql = "select 42;"
        migration_file = self.create_migration_file(migration_sql)
        connection = FakeConnection(migration_sql=migration_sql)

        result = apply_migration(connection, migration_file)

        self.assertEqual("applied", result)
        self.assertEqual(1, connection.transaction_entries)
        self.assertEqual([None], connection.transaction_exits)
        self.assertEqual(
            [
                ("SELECT 1 FROM schema_migrations WHERE version = %s", (migration_file.name,)),
                (migration_sql, None),
                ("INSERT INTO schema_migrations (version) VALUES (%s)", (migration_file.name,)),
            ],
            connection.executed,
        )

    def test_apply_migration_skip_does_not_run_migration_sql(self):
        migration_sql = "select 42;"
        migration_file = self.create_migration_file(migration_sql)
        connection = FakeConnection(
            migration_sql=migration_sql,
            already_applied=True,
        )

        result = apply_migration(connection, migration_file)

        self.assertEqual("skipped", result)
        self.assertEqual(1, connection.transaction_entries)
        self.assertEqual([None], connection.transaction_exits)
        self.assertEqual(1, len(connection.executed))
        self.assertEqual(
            ("SELECT 1 FROM schema_migrations WHERE version = %s", (migration_file.name,)),
            connection.executed[0],
        )

    def test_apply_migration_failure_does_not_record_schema_version(self):
        migration_sql = "select 42;"
        migration_file = self.create_migration_file(migration_sql)
        connection = FakeConnection(
            migration_sql=migration_sql,
            fail_on_migration_sql=True,
        )

        with self.assertRaisesRegex(RuntimeError, "migration exploded"):
            apply_migration(connection, migration_file)

        self.assertEqual(1, connection.transaction_entries)
        self.assertEqual([RuntimeError], connection.transaction_exits)
        self.assertEqual(
            [
                ("SELECT 1 FROM schema_migrations WHERE version = %s", (migration_file.name,)),
                (migration_sql, None),
            ],
            connection.executed,
        )

    def test_migration_url_precedence_prefers_explicit_migration_url(self):
        environment = {
            "DATABASE_URL": "postgresql://runtime.example/postgres",
            "SUPABASE_DATABASE_URL": "postgresql://supabase-runtime.example/postgres",
            "DATABASE_MIGRATION_URL": "postgresql://migration.example/postgres",
            "SUPABASE_MIGRATION_DATABASE_URL": (
                "postgresql://supabase-migration.example/postgres"
            ),
        }

        selected = select_migration_database_url(environment)

        self.assertEqual(environment["DATABASE_MIGRATION_URL"], selected)

    def test_supabase_migration_alias_precedes_runtime_urls(self):
        environment = {
            "DATABASE_URL": "postgresql://runtime.example/postgres",
            "SUPABASE_DATABASE_URL": "postgresql://supabase-runtime.example/postgres",
            "SUPABASE_MIGRATION_DATABASE_URL": (
                "postgresql://supabase-migration.example/postgres"
            ),
        }

        selected = select_migration_database_url(environment)

        self.assertEqual(environment["SUPABASE_MIGRATION_DATABASE_URL"], selected)


if __name__ == "__main__":
    unittest.main()
