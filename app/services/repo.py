from __future__ import annotations
from typing import Any, Dict, Optional
from psycopg.rows import dict_row
from app.db import get_connection
from app.services.queries import (
    SQL_CREATE_CONTACT,
    SQL_GET_TENANT_BY_CHATWOOT,
    SQL_GET_CONTACT_BY_PHONE_OR_EMAIL,
    SQL_UPDATE_CONTACT_FULL,
)

def get_tenant_by_chatwoot_account(account_id: int) -> Optional[Dict[str, Any]]:
    with get_connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(SQL_GET_TENANT_BY_CHATWOOT, {"account_id": account_id})
        return cur.fetchone()

def get_contact_by_phone_or_email(phone: str, email: str) -> Optional[Dict[str, Any]]:
    with get_connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(SQL_GET_CONTACT_BY_PHONE_OR_EMAIL, {"phone": phone, "email": email})
        return cur.fetchone()

def update_contact(
    *,
    first_name: Optional[str],
    last_name: Optional[str],
    email: Optional[str],
    phone: Optional[str],
    city: Optional[str],
    linkedin_url: Optional[str],
    facebook_url: Optional[str],
    instagram_url: Optional[str],
    github_url: Optional[str],
    x_url: Optional[str],
    company_id: Optional[int],
    chatwoot_contact_id: str,
    contact_id: int,
    twenty_person_id: Optional[str] = None,
) -> bool:
    """
    Keyword-only version: forces named arguments at callsite.
    Pass None to NULL-out a field.
    """
    params = {
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "phone": phone,
        "city": city,
        "linkedin_url": linkedin_url,
        "facebook_url": facebook_url,
        "instagram_url": instagram_url,
        "github_url": github_url,
        "x_url": x_url,
        "company_id": company_id,
        "chatwoot_contact_id": chatwoot_contact_id,
        "contact_id": contact_id,
        "twenty_person_id": twenty_person_id,
    }
    print("📡 Updating contact:", params)
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(SQL_UPDATE_CONTACT_FULL, params)
        return cur.rowcount > 0


def create_contact(
    *,
    tenant_id: int,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    city: Optional[str] = None,
    job_title: Optional[str] = None,
    linkedin_url: Optional[str] = None,
    facebook_url: Optional[str] = None,
    instagram_url: Optional[str] = None,
    github_url: Optional[str] = None,
    x_url: Optional[str] = None,
    company_id: Optional[int] = None,
    chatwoot_contact_id: Optional[str] = None,
    twenty_person_id: Optional[str] = None,
) -> int:
    """
    Simple create. Pass None for fields you don't have.
    Returns the new contact id.
    """
    params = {
        "tenant_id": tenant_id,
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "phone": phone,
        "city": city,
        "job_title": job_title,
        "linkedin_url": linkedin_url,
        "facebook_url": facebook_url,
        "instagram_url": instagram_url,
        "github_url": github_url,
        "x_url": x_url,
        "company_id": company_id,
        "chatwoot_contact_id": chatwoot_contact_id,
        "twenty_person_id": twenty_person_id,
    }

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(SQL_CREATE_CONTACT, params)
        new_id = cur.fetchone()[0]
        return new_id