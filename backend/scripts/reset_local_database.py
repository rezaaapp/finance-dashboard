import argparse
import os
import socket
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse, urlunparse

import psycopg
from dotenv import dotenv_values


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
EXPECTED_DATABASE = "finance_dashboard_local"
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
DATABASE_URL_KEYS = (
    "DATABASE_URL",
    "DATABASE_MIGRATION_URL",
    "SUPABASE_DATABASE_URL",
    "SUPABASE_MIGRATION_DATABASE_URL",
)


def load_local_environment():
    values = dict(os.environ)

    for key, value in dotenv_values(REPO_ROOT / ".env").items():
        if value is not None and key not in values:
            values[key] = value

    for key, value in dotenv_values(BACKEND_ROOT / ".env").items():
        if value is not None:
            values[key] = value

    return values


def parse_database_target(database_url):
    parsed = urlparse(database_url)
    host = (parsed.hostname or "").lower()
    database = unquote(parsed.path.lstrip("/"))

    if parsed.scheme not in {"postgres", "postgresql"}:
        raise ValueError("Database URL must use postgres or postgresql.")

    if "supabase" in host:
        raise ValueError("Supabase database hosts are never allowed.")

    if host not in LOCAL_HOSTS:
        raise ValueError(
            "Database host must be localhost, 127.0.0.1, or ::1."
        )

    if database != EXPECTED_DATABASE:
        raise ValueError(
            f"Database name must be exactly {EXPECTED_DATABASE}."
        )

    return parsed


def validate_configured_database_urls(environment):
    configured = {}

    for key in DATABASE_URL_KEYS:
        value = str(environment.get(key) or "").strip()

        if not value:
            continue

        configured[key] = parse_database_target(value)

    if "DATABASE_URL" not in configured:
        raise ValueError("DATABASE_URL is required for local reset.")

    selected_key = (
        "DATABASE_MIGRATION_URL"
        if "DATABASE_MIGRATION_URL" in configured
        else "DATABASE_URL"
    )

    return selected_key, configured[selected_key]


def build_admin_database_url(parsed_target):
    return urlunparse(parsed_target._replace(path="/postgres"))


def backend_port_is_open(port):
    for host in ("127.0.0.1", "::1"):
        family = socket.AF_INET6 if host == "::1" else socket.AF_INET

        try:
            with socket.socket(family, socket.SOCK_STREAM) as client:
                client.settimeout(0.25)

                if client.connect_ex((host, port)) == 0:
                    return True
        except OSError:
            continue

    return False


def reset_database(database_url, backend_port):
    parsed_target = parse_database_target(database_url)

    if backend_port_is_open(backend_port):
        raise RuntimeError(
            f"Backend appears active on port {backend_port}. Stop it before reset."
        )

    admin_database_url = build_admin_database_url(parsed_target)

    with psycopg.connect(admin_database_url, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                select count(*)
                from pg_stat_activity
                where datname = %s
                  and pid <> pg_backend_pid()
                """,
                (EXPECTED_DATABASE,),
            )
            active_connections = cursor.fetchone()[0]

            if active_connections:
                raise RuntimeError(
                    f"Reset refused: {active_connections} active connection(s) "
                    f"still use {EXPECTED_DATABASE}."
                )

            cursor.execute(
                "drop database if exists finance_dashboard_local"
            )
            cursor.execute(
                "create database finance_dashboard_local"
            )


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Drop and recreate the guarded local UAT PostgreSQL database."
    )
    parser.add_argument(
        "--confirm",
        required=True,
        help=f"Must be exactly: {EXPECTED_DATABASE}",
    )
    parser.add_argument(
        "--backend-port",
        type=int,
        default=8000,
        help="Local backend port that must not be listening (default: 8000).",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    if args.confirm != EXPECTED_DATABASE:
        print(
            f"Reset refused: --confirm must be exactly {EXPECTED_DATABASE}.",
            file=sys.stderr,
        )
        return 2

    try:
        environment = load_local_environment()
        selected_key, parsed_target = validate_configured_database_urls(environment)
        database_url = urlunparse(parsed_target)

        print(
            "Guard passed: "
            f"{selected_key} targets {parsed_target.hostname}/{EXPECTED_DATABASE}."
        )
        reset_database(database_url, args.backend_port)
    except (ValueError, RuntimeError, psycopg.Error) as error:
        print(f"Local database reset failed: {error}", file=sys.stderr)
        return 1

    print(f"Reset complete: {EXPECTED_DATABASE} was dropped and recreated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
