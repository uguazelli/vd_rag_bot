"""High-level database operations built on top of raw SQL statements."""

from __future__ import annotations

from typing import Any, Dict, Optional

from psycopg.rows import dict_row

from .connection import get_connection
from . import queries


def get_tenant_by_chatwoot_account_id(chatwoot_account_id: int) -> Optional[Dict[str, Any]]:
    """Return the tenant row for a Chatwoot account id or None if missing."""

    with get_connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            queries.SQL_GET_TENANT_BY_CHATWOOT_ACCOUNT_ID,
            {"chatwoot_account_id": chatwoot_account_id},
        )
        return cur.fetchone()


def get_contact_by_phone_or_email(phone: str, email: str) -> Optional[Dict[str, Any]]:
    """Find the first contact that matches the provided phone or email."""

    params = {"phone": phone, "email": email}
    with get_connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(queries.SQL_GET_CONTACT_BY_PHONE_OR_EMAIL, params)
        return cur.fetchone()


def create_contact(**params: Any) -> int:
    """Insert a new contact and return its id."""

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(queries.SQL_CREATE_CONTACT, params)
        new_id = cur.fetchone()[0]
        conn.commit()
        return int(new_id)


def update_contact(**params: Any) -> bool:
    """Update a contact record; return True when at least one row is affected."""

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(queries.SQL_UPDATE_CONTACT_FULL, params)
        conn.commit()
        return cur.rowcount > 0
