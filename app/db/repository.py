"""High-level database operations built on top of raw SQL statements."""

from __future__ import annotations

import os
import json
from datetime import date
from typing import Any, Dict

import anyio
from psycopg.rows import dict_row
from aiocache import Cache

from .connection import get_connection
from . import queries

# --- Cache backend: Memory now, flip to Redis via env without code changes ---
# MEMORY (default): no external service. For production, set CACHE_BACKEND=REDIS.
_BACKEND = os.getenv("CACHE_BACKEND", "MEMORY").upper()
_NAMESPACE = os.getenv("CACHE_NAMESPACE", "veridata")
_DEFAULT_TTL = int(os.getenv("CACHE_TTL_SECONDS", "300"))  # 5 minutes

if _BACKEND == "REDIS":
    _cache = Cache(
        Cache.REDIS,
        endpoint=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        password=os.getenv("REDIS_PASSWORD") or None,
        namespace=_NAMESPACE,
    )
else:
    _cache = Cache(Cache.MEMORY, namespace=_NAMESPACE)

async def get_params_by_omnichannel_id(omnichannel_id: int) -> Dict[str, Any]:
    """
    Async, cache-backed accessor.
    - Checks cache first (0 DB hits on cache hit).
    - On miss, runs the original sync query in a thread and caches the result.
    - Switch Memory → Redis by environment variables (no code changes).
    """
    key = f"client_params:{omnichannel_id}"
    cached = await _cache.get(key)
    if cached is not None:
        return cached

    # Original sync query wrapped in a function so we can run it in a worker thread
    def _query() -> Dict[str, Any]:
        with get_connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                queries.SQL_GET_PARAMS_BY_OMNICHANNEL_ID,
                {"omnichannel_id": omnichannel_id},
            )
            return cur.fetchone() or {}

    result = await anyio.to_thread.run_sync(_query)

    await _cache.set(key, result, ttl=_DEFAULT_TTL)
    return result


# Call this after you update the DB for that omnichannel_id
async def invalidate_params_cache(omnichannel_id: int) -> None:
    await _cache.delete(f"client_params:{omnichannel_id}")


async def get_params_by_tenant_id(tenant_id: int) -> Dict[str, Any]:
    """
    Fetch tenant configuration by tenant id (multi-tenant aware ingestion).
    """
    cache_key = f"tenant_params:{tenant_id}"
    cached = await _cache.get(cache_key)
    if cached is not None:
        return cached

    def _query() -> Dict[str, Any]:
        with get_connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                queries.SQL_GET_PARAMS_BY_TENANT_ID,
                {"tenant_id": tenant_id},
            )
            return cur.fetchone() or {}

    result = await anyio.to_thread.run_sync(_query)
    await _cache.set(cache_key, result, ttl=_DEFAULT_TTL)
    return result


async def increment_bot_request_count(tenant_id: int, bucket: date | None = None) -> int:
    """
    Increment the bot usage counter for a tenant and return the day's total.
    """
    target_bucket = bucket or date.today()

    def _increment() -> int:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    queries.SQL_INCREMENT_BOT_REQUEST_COUNT,
                    {"tenant_id": tenant_id, "bucket_date": target_bucket},
                )
                new_count = cur.fetchone()[0]
            conn.commit()
            return new_count

    return await anyio.to_thread.run_sync(_increment)


async def get_bot_request_total(tenant_id: int, start: date, end: date | None = None) -> int:
    """
    Return aggregated bot requests for a tenant between start and end dates (inclusive).
    """
    end_date = end or start

    def _fetch() -> int:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    queries.SQL_GET_BOT_REQUEST_COUNT_IN_RANGE,
                    {
                        "tenant_id": tenant_id,
                        "start_date": start,
                        "end_date": end_date,
                    },
                )
                row = cur.fetchone()
                return int(row[0]) if row and row[0] is not None else 0

    return await anyio.to_thread.run_sync(_fetch)
