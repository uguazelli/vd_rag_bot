# /workspace/app/db/connection.py
import os
import psycopg
from contextlib import contextmanager

def _database_dsn() -> str:
    host = os.getenv("DB_HOST", "host.docker.internal")
    port = os.getenv("DB_PORT", "5433")
    db   = os.getenv("DB_NAME", "vd")
    user = os.getenv("DB_USER", "vd")
    pwd  = os.getenv("DB_PASSWORD", "vd")
    return f"postgresql://{user}:{pwd}@{host}:{port}/{db}"

@contextmanager
def get_connection():
    conn = psycopg.connect(_database_dsn())
    try:
        yield conn
    finally:
        conn.close()
