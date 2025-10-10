import os
from typing import Any, Dict, Optional

import httpx

TWENTY_API_KEY = os.getenv("TWENTY_API_KEY")
TWENTY_BASE_URL = os.getenv("TWENTY_BASE_URL", "http://localhost:8000")


def _headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {TWENTY_API_KEY}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def _extract_id(data: Any) -> Optional[str]:
    if isinstance(data, dict):
        candidate = data.get("id")
        if isinstance(candidate, (str, int)):
            return str(candidate)
        for value in data.values():
            found = _extract_id(value)
            if found:
                return found
    elif isinstance(data, list):
        for item in data:
            found = _extract_id(item)
            if found:
                return found
    return None


def upsert_contact(
    client: httpx.Client,
    payload: Dict[str, Any],
    *,
    crm_id: Optional[str],
) -> Optional[str]:
    if not TWENTY_API_KEY:
        print("⚠️ Twenty API key missing; skipping sync.")
        return crm_id

    base = TWENTY_BASE_URL.rstrip("/")
    headers = _headers()
    params = {"depth": 1}

    if crm_id:
        print("🔄 Attempting to update Twenty contact:", crm_id)
        try:
            resp = client.patch(
                f"{base}/rest/people/{crm_id}",
                json=payload,
                headers=headers,
                params=params,
                timeout=10.0,
            )
            print("📥 Twenty PATCH response:", resp.status_code, resp.text)
            if resp.status_code < 300:
                data = resp.json() if resp.content else {}
                extracted = _extract_id(data) or crm_id
                print("✅ Twenty PATCH succeeded:", data)
                return str(extracted)
            if resp.status_code == 404:
                print("ℹ️ Twenty contact not found, will create new record.")
            else:
                print("❌ Twenty PATCH failed:", resp.status_code, resp.text)
                return crm_id
        except httpx.HTTPError as exc:
            print("❌ Twenty PATCH error:", exc)
            return crm_id

    print("➕ Creating new Twenty contact.")
    try:
        resp = client.post(
            f"{base}/rest/people",
            json=payload,
            headers=headers,
            params=params,
            timeout=10.0,
        )
        print("📥 Twenty POST response:", resp.status_code, resp.text)
        if resp.status_code < 300:
            data = resp.json() if resp.content else {}
            new_id = _extract_id(data)
            if new_id:
                print("✅ Twenty POST succeeded:", data)
                return str(new_id)
            print("⚠️ Twenty POST succeeded but no id found in response:", data)
        else:
            print("❌ Twenty POST failed:", resp.status_code, resp.text)
    except httpx.HTTPError as exc:
        print("❌ Twenty POST error:", exc)

    return crm_id
