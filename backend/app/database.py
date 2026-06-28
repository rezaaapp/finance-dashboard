from contextlib import contextmanager
from threading import Lock

import psycopg
from psycopg_pool import ConnectionPool

from app.config import settings


def _get_connection_kwargs():
    if not settings.DATABASE_SSL:
        return {}

    return {
        "sslmode": "verify-full"
        if settings.DATABASE_SSL_REJECT_UNAUTHORIZED
        else "require"
    }


def get_migration_database_url():
    return settings.DATABASE_MIGRATION_URL or settings.DATABASE_URL


pool = None
_pool_open_lock = Lock()


def _create_pool():
    if not settings.DATABASE_URL:
        raise ValueError("DATABASE_URL is not configured")

    return ConnectionPool(
        conninfo=settings.DATABASE_URL,
        min_size=0,
        max_size=settings.DATABASE_POOL_MAX,
        kwargs=_get_connection_kwargs(),
        open=False,
    )


def ensure_pool_open():
    global pool

    if pool is None:
        with _pool_open_lock:
            if pool is None:
                pool = _create_pool()

    if not pool.closed:
        return

    with _pool_open_lock:
        if pool.closed:
            pool.open()


def close_database_pool():
    if pool is not None and not pool.closed:
        pool.close()


@contextmanager
def get_db_connection():
    ensure_pool_open()

    with pool.connection() as connection:
        yield connection


@contextmanager
def get_migration_connection():
    migration_database_url = get_migration_database_url()

    if not migration_database_url:
        raise ValueError("DATABASE_URL is not configured")

    connection = psycopg.connect(
        migration_database_url,
        **_get_connection_kwargs(),
    )

    try:
        yield connection
    finally:
        connection.close()


def check_database_connection():
    try:
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()

        return {
            "ok": True,
            "message": "connected",
        }
    except Exception:
        return {
            "ok": False,
            "message": "database connection failed",
        }


def get_migration_status():
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("select to_regclass('public.schema_migrations')")

            if cursor.fetchone()[0] is None:
                return {
                    "table_found": False,
                    "count": 0,
                    "latest": None,
                }

            cursor.execute(
                """
                select count(*)::int, max(version)
                from public.schema_migrations
                """
            )
            count, latest = cursor.fetchone()

    return {
        "table_found": True,
        "count": count,
        "latest": latest,
    }
