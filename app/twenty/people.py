from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

from app.config import settings
from app.twenty.client import upsert_contact

TWENTY_API_KEY = settings.twenty_api_key
TWENTY_BASE_URL = settings.twenty_base_url.rstrip("/")
TIMEOUT = 10.0
DEFAULT_PARAMS = {"depth": 1, "limit": 1}


def _headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {TWENTY_API_KEY}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def _request(
    client: httpx.Client,
    method: str,
    path: str,
    *,
    params: Optional[Dict[str, Any]] = None,
) -> Optional[httpx.Response]:
    if not TWENTY_API_KEY:
        print("⚠️ Twenty API key missing; cannot issue request.")
        return None

    try:
        return client.request(
            method,
            f"{TWENTY_BASE_URL}{path}",
            headers=_headers(),
            params=params,
            timeout=TIMEOUT,
        )
    except httpx.HTTPError as exc:
        print(f"❌ Twenty {method.upper()} error:", exc)
        return None


def _extract_first_person(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        return None
    people = data.get("people")
    if isinstance(people, list) and people:
        first = people[0]
        return first if isinstance(first, dict) else None
    return None


def get_people_by_id(
    client: httpx.Client, person_id: str, *, depth: int = 1
) -> Optional[Dict[str, Any]]:
    if not person_id:
        return None
    resp = _request(
        client,
        "get",
        f"/rest/people/{person_id}",
        params={"depth": depth},
    )
    if resp is None or resp.status_code >= 300:
        if resp is not None:
            print("❌ Failed to fetch Twenty person:", resp.status_code, resp.text)
        return None
    payload = resp.json() if resp.content else {}
    return payload.get("data", {}).get("person")


def get_people_chatwoot_id(
    client: httpx.Client, chatwoot_id: str
) -> Optional[Dict[str, Any]]:
    if not chatwoot_id:
        return None
    params = {
        **DEFAULT_PARAMS,
        "filter": f"chatwootId[eq]:{chatwoot_id}",
    }
    resp = _request(client, "get", "/rest/people", params=params)
    if resp is None or resp.status_code >= 300:
        if resp is not None:
            print(
                "❌ Failed to search Twenty people by chatwootId:",
                resp.status_code,
                resp.text,
            )
        return None
    payload = resp.json() if resp.content else {}
    return _extract_first_person(payload)


def create_or_update_people(
    client: httpx.Client,
    *,
    chatwoot_id: Optional[str],
    payload: Dict[str, Any],
    crm_id: Optional[str] = None,
) -> Optional[str]:
    if not TWENTY_API_KEY:
        print("⚠️ Twenty API key missing; skipping sync.")
        return None

    clean_payload = dict(payload)
    if chatwoot_id:
        clean_payload["chatwootId"] = str(chatwoot_id)

    existing_id: Optional[str] = None
    if crm_id:
        existing_id = crm_id
    elif chatwoot_id:
        existing = get_people_chatwoot_id(client, chatwoot_id)
        if isinstance(existing, dict):
            existing_id = existing.get("id")

    return upsert_contact(client, clean_payload, crm_id=existing_id)
