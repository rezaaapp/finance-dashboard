from pathlib import Path
import os
import sys


BACKEND_ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS_DIR = BACKEND_ROOT / "db" / "migrations"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


SCHEMA_MIGRATIONS_SQL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
  version TEXT PRIMARY KEY,
  applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


def safe_error_message(action, error):
    return (
        f"{action} failed: {error.__class__.__name__}. "
        "Details hidden to avoid exposing database connection information."
    )


def select_migration_database_url(environment=None):
    configured = environment if environment is not None else os.environ
    return (
        configured.get("DATABASE_MIGRATION_URL")
        or configured.get("SUPABASE_MIGRATION_DATABASE_URL")
        or configured.get("DATABASE_URL")
        or configured.get("SUPABASE_DATABASE_URL")
    )


def load_database_helper():
    migration_database_url = select_migration_database_url()
    if migration_database_url:
        # app.config validates DATABASE_URL at import time. For this dedicated
        # runner, validate the exact migration target selected above rather
        # than a stale runtime URL from a local dotenv file.
        os.environ["DATABASE_URL"] = migration_database_url

    from app.database import get_migration_connection

    return get_migration_connection


def get_migration_files():
    return sorted(MIGRATIONS_DIR.glob("*.sql"), key=lambda path: path.name)


def ensure_schema_migrations(connection):
    with connection.transaction():
        with connection.cursor() as cursor:
            cursor.execute(SCHEMA_MIGRATIONS_SQL)


def apply_migration(connection, migration_file):
    version = migration_file.name
    sql = migration_file.read_text(encoding="utf-8")

    with connection.transaction():
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM schema_migrations WHERE version = %s",
                (version,),
            )

            if cursor.fetchone():
                return "skipped"

            print(f"Applying migration: {version}")
            cursor.execute(sql)
            cursor.execute(
                "INSERT INTO schema_migrations (version) VALUES (%s)",
                (version,),
            )

    return "applied"


def run_migrations():
    get_migration_connection = load_database_helper()
    migration_files = get_migration_files()

    if not migration_files:
        print(f"No migration files found in {MIGRATIONS_DIR}.")
        return 0

    print(f"Found {len(migration_files)} migration file(s).")

    for migration_file in migration_files:
        print(f"Migration file found: {migration_file.name}")

    with get_migration_connection() as connection:
        ensure_schema_migrations(connection)

        for migration_file in migration_files:
            try:
                result = apply_migration(connection, migration_file)
            except Exception as error:
                print(safe_error_message(
                    f"Migration {migration_file.name}",
                    error,
                ))
                return 1

            if result == "skipped":
                print(f"Skipping already applied migration: {migration_file.name}")
            else:
                print(f"Applied successfully: {migration_file.name}")

    return 0


def main():
    try:
        return run_migrations()
    except Exception as error:
        print(safe_error_message("Migration runner", error))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
