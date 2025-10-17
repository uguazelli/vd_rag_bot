from typing import Any, Dict, Optional
import httpx
from app.config import settings

TWENTY_API_KEY = settings.twenty_api_key
TWENTY_BASE_URL = settings.twenty_base_url.rstrip("/")
TIMEOUT = 10.0
DEFAULT_PARAMS = {"depth": 1}


def _headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {TWENTY_API_KEY}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def _extract_id(payload: Any) -> Optional[str]:
    if isinstance(payload, dict):
        value = payload.get("id")
        if isinstance(value, (str, int)):
            return str(value)
        for nested in payload.values():
            found = _extract_id(nested)
            if found:
                return found
    elif isinstance(payload, list):
        for item in payload:
            found = _extract_id(item)
            if found:
                return found
    return None


def _request( client: httpx.Client, method: str, path: str, *, payload: Dict[str, Any], ) -> Optional[httpx.Response]:
    try:
        return client.request(
            method,
            f"{TWENTY_BASE_URL}{path}",
            json=payload,
            headers=_headers(),
            params=DEFAULT_PARAMS,
            timeout=TIMEOUT,
        )
    except httpx.HTTPError as exc:
        print(f"❌ Twenty {method.upper()} error:", exc)
        return None


def _handle_success(resp: httpx.Response, fallback_id: Optional[str]) -> Optional[str]:
    data = resp.json() if resp.content else {}
    contact_id = _extract_id(data) or fallback_id
    if contact_id:
        print("✅ Twenty request succeeded.")
        return str(contact_id)
    print("⚠️ Twenty request succeeded but no contact id found:", data)
    return fallback_id


def upsert_contact(
    client: httpx.Client,
    payload: Dict[str, Any],
    *,
    crm_id: Optional[str],
) -> Optional[str]:
    if not TWENTY_API_KEY:
        print("⚠️ Twenty API key missing; skipping sync.")
        return crm_id

    if crm_id:
        print(f"🔄 Updating Twenty contact {crm_id}")
        resp = _request(client, "patch", f"/rest/people/{crm_id}", payload=payload)
        if resp is None:
            return crm_id
        if resp.status_code < 300:
            return _handle_success(resp, crm_id)
        if resp.status_code != 404:
            print("❌ Twenty PATCH failed:", resp.status_code, resp.text)
            return crm_id
        print("ℹ️ Twenty contact not found; will create new record.")

    print("➕ Creating new Twenty contact.")
    resp = _request(client, "post", "/rest/people", payload=payload)
    if resp is None:
        return crm_id
    if resp.status_code < 300:
        return _handle_success(resp, None)

    print("❌ Twenty POST failed:", resp.status_code, resp.text)
    return crm_id
