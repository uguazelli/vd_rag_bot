from __future__ import annotations

import os
from contextlib import contextmanager
import psycopg

# Use localhost if running from your Mac; use "db" if running inside the compose network.
DATABASE_URL = os.getenv("DATABASE_URL")

def _normalize_conninfo(url: str) -> str:
    """Strip async/driver prefixes like postgresql+psycopg:// to plain postgresql://."""
    if "://" not in url:
        return url
    scheme, rest = url.split("://", 1)
    if "+" in scheme:
        base = scheme.split("+", 1)[0]
        return f"{base}://{rest}"
    return url

def _connect():
    conninfo = _normalize_conninfo(DATABASE_URL)
    return psycopg.connect(conninfo, autocommit=False)

from contextlib import contextmanager
@contextmanager
def get_connection():
    conn = _connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

# -----------------------------
# DDL
# -----------------------------

# Drop link tables entirely (we’re denormalizing the external IDs into main tables)
DDL_DROP_ORDER = [
    "contacts",
    "companies",
    "tenants",
]

DDL_CREATE = [
    # 0) helper function for updated_at
    """
    CREATE OR REPLACE FUNCTION set_updated_at()
    RETURNS TRIGGER AS $$
    BEGIN
      NEW.updated_at = NOW();
      RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """,

    # 1) tenants
    """
    CREATE TABLE IF NOT EXISTS tenants (
        id BIGSERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        chatwoot_account_id INTEGER UNIQUE,
        chatwoot_api_url TEXT NOT NULL,
        chatwoot_bot_token TEXT NOT NULL,
        twenty_workspace_id TEXT NOT NULL,
        twenty_api_key TEXT NOT NULL,
        twenty_base_url TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT NOW()
    );
    """,

    # 2) companies  (external IDs now live here)
    """
    CREATE TABLE IF NOT EXISTS companies (
        id BIGSERIAL PRIMARY KEY,
        tenant_id BIGINT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
        name TEXT,
        address JSONB,
        annual_recurring_revenue NUMERIC(18,2),
        domain_name TEXT,
        employees INTEGER,
        is_icp BOOLEAN,
        linkedin_url TEXT,
        account_owner TEXT,
        city TEXT,
        -- external IDs
        chatwoot_company_id TEXT,
        twenty_company_id   TEXT,
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    );
    """,
    # trigger for companies
    """
    DROP TRIGGER IF EXISTS trg_companies_updated_at ON companies;
    CREATE TRIGGER trg_companies_updated_at
      BEFORE UPDATE ON companies
      FOR EACH ROW EXECUTE FUNCTION set_updated_at();
    """,

    # 3) contacts (external IDs now live here)
    """
    CREATE TABLE IF NOT EXISTS contacts (
        id BIGSERIAL PRIMARY KEY,
        tenant_id BIGINT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
        first_name TEXT,
        last_name TEXT,
        email TEXT,
        phone TEXT,
        city TEXT,
        job_title TEXT,
        linkedin_url TEXT,
        facebook_url TEXT,
        instagram_url TEXT,
        github_url TEXT,
        x_url TEXT,
        company_id BIGINT REFERENCES companies(id),
        chatwoot_contact_id TEXT,
        twenty_person_id    TEXT,
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    );
    """,
    # trigger for contacts
    """
    DROP TRIGGER IF EXISTS trg_contacts_updated_at ON contacts;
    CREATE TRIGGER trg_contacts_updated_at
      BEFORE UPDATE ON contacts
      FOR EACH ROW EXECUTE FUNCTION set_updated_at();
    """,

    # 4) indexes / constraints that help syncing & lookups

    # CONTACTS: unique per-tenant email/phone (ignore NULLs); case-insensitive email
    """
    CREATE UNIQUE INDEX IF NOT EXISTS uq_contacts_tenant_email
      ON contacts(tenant_id, lower(email))
      WHERE email IS NOT NULL;
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS uq_contacts_tenant_phone
      ON contacts(tenant_id, phone)
      WHERE phone IS NOT NULL;
    """,

    # CONTACTS: unique per-tenant external IDs (ignore NULLs)
    """
    CREATE UNIQUE INDEX IF NOT EXISTS uq_contacts_tenant_chatwoot
      ON contacts(tenant_id, chatwoot_contact_id)
      WHERE chatwoot_contact_id IS NOT NULL;
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS uq_contacts_tenant_twenty
      ON contacts(tenant_id, twenty_person_id)
      WHERE twenty_person_id IS NOT NULL;
    """,

    # COMPANIES: unique per-tenant domain and external IDs (ignore NULLs)
    """
    CREATE UNIQUE INDEX IF NOT EXISTS uq_companies_tenant_domain
      ON companies(tenant_id, domain_name)
      WHERE domain_name IS NOT NULL;
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS uq_companies_tenant_chatwoot
      ON companies(tenant_id, chatwoot_company_id)
      WHERE chatwoot_company_id IS NOT NULL;
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS uq_companies_tenant_twenty
      ON companies(tenant_id, twenty_company_id)
      WHERE twenty_company_id IS NOT NULL;
    """,

    # quick lookups
    "CREATE INDEX IF NOT EXISTS ix_contacts_company_id ON contacts(company_id);",
    "CREATE INDEX IF NOT EXISTS ix_contacts_tenant_id  ON contacts(tenant_id);",
    "CREATE INDEX IF NOT EXISTS ix_companies_tenant_id ON companies(tenant_id);",
]

# -----------------------------
# Ops
# -----------------------------

def drop_all() -> None:
    """Drop known tables in FK-safe order."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            for table in DDL_DROP_ORDER:
                cur.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")

def init_db() -> None:
    """Create schema, triggers, and indexes."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            for stmt in DDL_CREATE:
                cur.execute(stmt)

def reset_db() -> None:
    drop_all()
    init_db()

# -----------------------------
# CLI
# -----------------------------

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Initialize or reset the Postgres schema.")
    parser.add_argument("--reset", action="store_true", help="Drop and recreate all tables")
    args = parser.parse_args()

    print("Using DATABASE_URL:", os.getenv("DATABASE_URL", "<not set>"))
    if args.reset:
        reset_db()
        print("✅ DB reset complete.")
    else:
        init_db()
        print("✅ DB init complete.")
