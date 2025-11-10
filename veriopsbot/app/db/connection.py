# /workspace/app/db/connection.py
import os
from contextlib import contextmanager
from typing import Tuple

import psycopg


def _database_dsn() -> str:
    host = os.getenv("POSTGRES_HOST", "host.docker.internal")
    port = os.getenv("POSTGRES_PORT", "5433")
    db = os.getenv("POSTGRES_DATABASE", "vd")
    user = os.getenv("POSTGRES_USERNAME", "vd")
    pwd = os.getenv("POSTGRES_PASSWORD", "vd")
    return f"postgresql://{user}:{pwd}@{host}:{port}/{db}"


def resolve_database_dsn() -> str:
    """Expose the psycopg-friendly connection string."""
    return _database_dsn()


def resolve_sqlalchemy_urls() -> Tuple[str, str]:
    """Return sync/async URLs suitable for SQLAlchemy/llamaindex usage."""
    dsn = resolve_database_dsn()
    if dsn.startswith("postgresql://"):
        sync_url = dsn.replace("postgresql://", "postgresql+psycopg://", 1)
        async_url = dsn.replace("postgresql://", "postgresql+asyncpg://", 1)
    else:
        sync_url = dsn
        async_url = dsn
    return sync_url, async_url


@contextmanager
def get_connection():
    conn = psycopg.connect(_database_dsn())
    try:
        yield conn
    finally:
        conn.close()
