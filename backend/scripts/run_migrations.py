from pathlib import Path
import os
import re
import sys
from urllib.parse import unquote, urlparse


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


def _env_bool(environment, key, default="true"):
    return str(environment.get(key, default)).strip().lower() in {
        "1", "true", "yes", "on"
    }


def _mask_host(host):
    normalized = str(host or "").strip()
    if not normalized:
        return "(not configured)"
    if normalized in {"localhost", "127.0.0.1", "::1"}:
        return normalized

    parts = normalized.split(".")
    if len(parts) >= 3:
        return f"{parts[0][:2]}***.{'.'.join(parts[-2:])}"
    return "***"


def _sanitize_exception_message(message, database_url=None):
    sanitized = str(message or "").strip() or "(no message)"
    parsed = urlparse(database_url or "")

    if database_url:
        sanitized = sanitized.replace(database_url, "<redacted-database-url>")
    for credential in (parsed.username, parsed.password):
        if credential:
            sanitized = sanitized.replace(unquote(credential), "***")

    sanitized = re.sub(
        r"(?i)\b(user(?:name)?|password|passfile)\s*=\s*([^\s]+)",
        r"\1=***",
        sanitized,
    )
    sanitized = re.sub(
        r'(?i)\bfor user\s+["\']?[^"\'\s]+["\']?',
        'for user "***"',
        sanitized,
    )
    sanitized = re.sub(
        r"(?i)(postgres(?:ql)?://)[^\s/@:]+(?::[^\s/@]*)?@",
        r"\1***:***@",
        sanitized,
    )
    return sanitized


def _exception_chain(error):
    chain = []
    seen = set()
    current = error
    while current is not None and id(current) not in seen and len(chain) < 5:
        seen.add(id(current))
        chain.append(current)
        current = current.__cause__ or current.__context__
    return chain


def safe_error_message(action, error, database_url=None, environment=None):
    configured = environment if environment is not None else os.environ
    selected_url = database_url or select_migration_database_url(configured)
    parsed = urlparse(selected_url or "")
    try:
        port = parsed.port or 5432
    except ValueError:
        port = "invalid"

    lines = [
        f"{action} failed.",
        f"Migration host: {_mask_host(parsed.hostname)}",
        f"Migration port: {port}",
        f"SSL enabled: {'yes' if _env_bool(configured, 'DATABASE_SSL') else 'no'}",
        "SSL reject unauthorized: "
        + ("yes" if _env_bool(configured, "DATABASE_SSL_REJECT_UNAUTHORIZED") else "no"),
    ]
    for index, exception in enumerate(_exception_chain(error)):
        label = "Exception" if index == 0 else f"Caused by {index}"
        message = _sanitize_exception_message(exception, selected_url)
        lines.append(f"{label} ({exception.__class__.__name__}): {message}")

    return "\n".join(lines)


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
