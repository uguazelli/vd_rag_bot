"""Database connection helpers.

This module centralises how the application obtains PostgreSQL connections so
all callers share the same environment-driven configuration.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

import psycopg


def _database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL environment variable is required for database access.")
    return url


@contextmanager
def get_connection() -> Iterator[psycopg.Connection]:
    """Yield a Postgres connection configured from the environment."""

    conn: psycopg.Connection | None = None
    try:
        conn = psycopg.connect(_database_url())
        yield conn
    finally:
        if conn is not None:
            conn.close()
