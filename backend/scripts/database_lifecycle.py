import argparse
import os
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

import psycopg


BACKEND_ROOT = Path(__file__).resolve().parents[1]
LOCAL_DATABASE = "finance_dashboard_local"
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
SUPABASE_RESET_PHRASE = "RESET SUPABASE OMON"
SUPABASE_MIGRATE_PHRASE = "MIGRATE SUPABASE OMON"
PROFILES = {
    "local-dev": {"db_target": "postgres-local"},
    "local-prod": {"db_target": "supabase"},
}
COUNT_TABLES = {
    "user count": "users",
    "workspace count": "workspaces",
    "transaction count": "transactions",
    "import job count": "import_jobs",
    "draft count": "import_draft_transactions",
    "fingerprint registry count": "import_transaction_registry",
    "budget count": "budgets",
}


def parse_database_target(database_url, target):
    parsed = urlparse(str(database_url or "").strip())
    host = (parsed.hostname or "").lower()
    database = unquote(parsed.path.lstrip("/"))
    if parsed.scheme not in {"postgres", "postgresql"}:
        raise ValueError("Database URL must use postgres or postgresql.")
    if not host or not database:
        raise ValueError("Database URL must include a host and database name.")
    if target == "local-dev":
        if "supabase" in host:
            raise ValueError("local-dev rejects Supabase database hosts.")
        if host not in LOCAL_HOSTS:
            raise ValueError("local-dev database host must be loopback.")
        if database != LOCAL_DATABASE:
            raise ValueError(f"local-dev database must be {LOCAL_DATABASE}.")
    elif target == "local-prod":
        if host in LOCAL_HOSTS:
            raise ValueError("local-prod rejects loopback database hosts.")
        if "supabase" not in host:
            raise ValueError("local-prod database host must be Supabase.")
    else:
        raise ValueError(f"Unsupported database target: {target}.")
    return parsed


def validate_environment(environment, target, action, confirmation=None):
    expected = {
        "APP_ENV": target,
        "ENV_PROFILE": target,
        "DB_TARGET": PROFILES[target]["db_target"],
    }
    for key, expected_value in expected.items():
        if str(environment.get(key) or "").strip() != expected_value:
            raise ValueError(f"{key} must be {expected_value}.")
    selected_key = (
        "DATABASE_MIGRATION_URL"
        if str(environment.get("DATABASE_MIGRATION_URL") or "").strip()
        else "DATABASE_URL"
    )
    database_url = str(environment.get(selected_key) or "").strip()
    parsed = parse_database_target(database_url, target)
    required_phrase = None
    if target == "local-prod" and action == "reset":
        required_phrase = SUPABASE_RESET_PHRASE
    elif target == "local-prod" and action == "migrate":
        required_phrase = SUPABASE_MIGRATE_PHRASE
    if required_phrase and confirmation != required_phrase:
        raise ValueError(f"Confirmation phrase must be exactly: {required_phrase}")
    return selected_key, database_url, parsed


def mask_database_host(host):
    normalized = str(host or "").strip().lower()
    if normalized in LOCAL_HOSTS:
        return normalized
    labels = normalized.split(".")
    if len(labels) < 3:
        return "***"
    return f"{labels[0]}.***.{'.'.join(labels[-2:])}"


def run_migrations(database_url):
    os.environ["DATABASE_URL"] = database_url
    os.environ["DATABASE_MIGRATION_URL"] = database_url
    if str(BACKEND_ROOT) not in sys.path:
        sys.path.insert(0, str(BACKEND_ROOT))
    from scripts.run_migrations import run_migrations as project_runner
    return project_runner()


def reset_local_database(database_url, backend_port):
    if str(BACKEND_ROOT) not in sys.path:
        sys.path.insert(0, str(BACKEND_ROOT))
    from scripts.reset_local_database import reset_database
    reset_database(database_url, backend_port)


def reset_supabase_schema(database_url):
    with psycopg.connect(database_url, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute("drop schema if exists public cascade")
            cursor.execute("create schema public")
            cursor.execute("grant all on schema public to postgres")
            cursor.execute("grant all on schema public to public")


def seed_baseline(database_url, environment):
    email = str(environment.get("SEED_USER_EMAIL") or "").strip().lower()
    name = str(environment.get("SEED_USER_NAME") or "").strip()
    workspace_name = str(
        environment.get("SEED_WORKSPACE_NAME") or "Admin's Household"
    ).strip()
    if not email or not name or not workspace_name:
        raise ValueError(
            "SEED_USER_EMAIL, SEED_USER_NAME, and SEED_WORKSPACE_NAME are required."
        )

    with psycopg.connect(database_url) as connection:
        with connection.transaction():
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    insert into users (email, name, role)
                    values (%s, %s, 'owner')
                    on conflict (email) do update
                    set name = excluded.name, role = 'owner'
                    returning id
                    """,
                    (email, name),
                )
                user_id = cursor.fetchone()[0]
                cursor.execute(
                    """
                    select w.id from workspaces w
                    join workspace_members wm on wm.workspace_id = w.id
                    where wm.user_id = %s and wm.role = 'owner'
                    order by w.created_at limit 1
                    """,
                    (user_id,),
                )
                row = cursor.fetchone()
                if row:
                    workspace_id = row[0]
                    cursor.execute(
                        "update workspaces set name = %s where id = %s",
                        (workspace_name, workspace_id),
                    )
                else:
                    cursor.execute(
                        """
                        insert into workspaces (name, subscription_status)
                        values (%s, 'free') returning id
                        """,
                        (workspace_name,),
                    )
                    workspace_id = cursor.fetchone()[0]
                cursor.execute(
                    """
                    insert into workspace_members (workspace_id, user_id, role)
                    values (%s, %s, 'owner')
                    on conflict (workspace_id, user_id)
                    do update set role = 'owner'
                    """,
                    (workspace_id, user_id),
                )
    return email, workspace_name


def query_database_summary(database_url):
    summary = {}
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute("select count(*)::int, max(version) from schema_migrations")
            migration_count, latest_version = cursor.fetchone()
            summary["migration count"] = migration_count
            summary["latest migration version"] = latest_version or "none"
            for label, table in COUNT_TABLES.items():
                cursor.execute(f"select count(*)::int from public.{table}")
                summary[label] = cursor.fetchone()[0]
    return summary


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Guarded Omon database lifecycle.")
    parser.add_argument("--target", required=True, choices=sorted(PROFILES))
    parser.add_argument(
        "--action", required=True, choices=("migrate", "reset", "seed", "verify")
    )
    parser.add_argument("--confirm")
    parser.add_argument("--backend-port", type=int, default=8000)
    parser.add_argument("--validate-only", action="store_true")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    try:
        selected_key, database_url, parsed = validate_environment(
            os.environ, args.target, args.action, args.confirm
        )
        print(f"APP_ENV                 : {args.target}")
        print(f"ENV_PROFILE             : {args.target}")
        print(f"DB_TARGET               : {PROFILES[args.target]['db_target']}")
        print(f"Database URL source     : {selected_key}")
        print(f"Database host (masked)  : {mask_database_host(parsed.hostname)}")
        print(f"Database name           : {unquote(parsed.path.lstrip('/'))}")
        print("Secrets                 : hidden")
        if args.validate_only:
            print(f"Validation passed for {args.target} {args.action}.")
            return 0
        if args.action == "migrate":
            return run_migrations(database_url)
        if args.action == "reset" and args.target == "local-dev":
            reset_local_database(database_url, args.backend_port)
            print(f"Reset complete: {LOCAL_DATABASE} was recreated.")
            return 0
        if args.action == "reset":
            reset_supabase_schema(database_url)
            print("Reset complete: Supabase public schema was recreated.")
            return 0
        if args.action == "seed":
            email, workspace = seed_baseline(database_url, os.environ)
            print(f"Baseline seed ready: owner {email}, workspace {workspace}.")
            return 0
        for label, value in query_database_summary(database_url).items():
            print(f"{label:<25}: {value}")
        return 0
    except (ValueError, RuntimeError) as error:
        print(f"Lifecycle refused: {error}", file=sys.stderr)
        return 2
    except psycopg.Error:
        print(
            "Database lifecycle failed: database error. Connection details hidden.",
            file=sys.stderr,
        )
        return 1
    except Exception as error:
        print(
            f"Database lifecycle failed: {error.__class__.__name__}. Details hidden.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
