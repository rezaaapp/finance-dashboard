from contextlib import contextmanager
from threading import Lock

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


pool = ConnectionPool(
    conninfo=settings.DATABASE_URL,
    min_size=0,
    max_size=settings.DATABASE_POOL_MAX,
    kwargs=_get_connection_kwargs(),
    open=False,
)
_pool_open_lock = Lock()


def ensure_pool_open():
    if not pool.closed:
        return

    with _pool_open_lock:
        if pool.closed:
            pool.open()


def close_database_pool():
    if not pool.closed:
        pool.close()


@contextmanager
def get_db_connection():
    ensure_pool_open()

    with pool.connection() as connection:
        yield connection
