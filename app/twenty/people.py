from __future__ import annotations
from typing import Dict, Optional
import httpx
from app.config import settings

BASE_URL = settings.twenty_base_url.rstrip("/")
HEADERS = {
    "Authorization": f"Bearer {settings.twenty_api_key}",
    "Accept": "application/json",
    "Content-Type": "application/json",
}
TIMEOUT = 10.0


def get_people_by_id(client: httpx.Client, person_id: str, *, depth: int = 1) -> Optional[Dict]:
    try:
        resp = client.get(
            f"{BASE_URL}/rest/people/{person_id}",
            headers=HEADERS,
            params={"depth": depth},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        print("❌ Failed to fetch Twenty person:", exc)
        return None

    data = resp.json().get("data") or {}
    return data.get("person")


def get_people_chatwoot_id(
    client: httpx.Client, chatwoot_id: str
) -> Optional[Dict]:
    try:
        resp = client.get(
            f"{BASE_URL}/rest/people",
            headers=HEADERS,
            params={
                "filter": f"chatwootId[eq]:{chatwoot_id}",
                "limit": 1,
                "depth": 1,
            },
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        print("❌ Failed to search Twenty people by chatwootId:", exc)
        return None

    people = ((resp.json().get("data") or {}).get("people")) or []
    return people[0] if people else None


def create_person(client: httpx.Client, payload: Dict) -> Optional[str]:
    try:
        resp = client.post(
            f"{BASE_URL}/rest/people",
            headers=HEADERS,
            params={"depth": 1},
            json=payload,
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        print("❌ Twenty create person failed:", exc)
        return None

    record = (resp.json().get("data") or {}).get("createPerson") or {}
    return record.get("id")


def update_person(
    client: httpx.Client, person_id: str, payload: Dict
) -> Optional[str]:
    try:
        resp = client.patch(
            f"{BASE_URL}/rest/people/{person_id}",
            headers=HEADERS,
            params={"depth": 1},
            json=payload,
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        print("❌ Twenty update person failed:", exc)
        return None

    record = (resp.json().get("data") or {}).get("updatePerson") or {}
    return record.get("id") or person_id


def create_or_update_people(
    client: httpx.Client,
    *,
    chatwoot_id: str,
    payload: Dict,
) -> Optional[str]:
    if not chatwoot_id:
        print("⚠️ Missing chatwoot_id; skipping Twenty sync.")
        return None

    body = dict(payload)
    body["chatwootId"] = str(chatwoot_id)

    existing = get_people_chatwoot_id(client, chatwoot_id)
    person_id = existing.get("id") if existing else None

    if person_id:
        return update_person(client, str(person_id), body) or person_id
    return create_person(client, body)
