import re
from typing import Any, Dict, Optional
import httpx
from app.config import settings
from app.twenty.people import create_or_update_people

CHATWOOT_API_URL = settings.chatwoot_api_url.rstrip("/")
CHATWOOT_BOT_TOKEN = settings.chatwoot_bot_access_token or "nS7yBjTg66L29cSUVypLQnGB"
TIMEOUT = 10.0


def _headers_chatwoot() -> Dict[str, str]:
    return {"Content-Type": "application/json", "api_access_token": CHATWOOT_BOT_TOKEN}


def _clean(value: Optional[str]) -> Optional[str]:
    return value.strip() or None if isinstance(value, str) else None


def _split_name(full_name: Optional[str]) -> Dict[str, str]:
    if not full_name:
        return {}
    parts = re.split(r"\s+", full_name.strip())
    if not parts:
        return {}
    first = parts[0]
    rest = " ".join(parts[1:]) if len(parts) > 1 else None
    return {k: v for k, v in (("firstName", first), ("lastName", rest)) if v}


def _extract_contact_payload(contact: Dict[str, Any]) -> Dict[str, Any]:
    additional = contact.get("additional_attributes") or {}
    social = additional.get("social_profiles") or {}

    payload: Dict[str, Any] = {"createdBy": {"source": "API"}}

    if name_parts := _split_name(_clean(contact.get("name"))):
        payload["name"] = name_parts
    if (email := _clean(contact.get("email"))):
        payload["emails"] = {"primaryEmail": email}
    if (phone := _clean(contact.get("phone_number"))):
        payload["phones"] = {"primaryPhoneNumber": phone}
    if (linkedin := _clean(social.get("linkedin"))):
        payload["linkedinLink"] = {"primaryLinkUrl": linkedin}
    if (x_link := _clean(social.get("twitter"))):
        payload["xLink"] = {"primaryLinkUrl": x_link}
    if (city := _clean(additional.get("city"))):
        payload["city"] = city

    return payload


def _sync_crm_id(
    client: httpx.Client,
    account_id: Optional[int],
    contact_id: Optional[int],
    crm_id: Optional[str],
) -> bool:
    if not crm_id:
        print("⚠️ No crm_id computed; skipping Chatwoot update.")
        return False
    if not (account_id and contact_id):
        print("⚠️ Missing account or contact id; cannot push crm_id to Chatwoot.")
        return False

    url = f"{CHATWOOT_API_URL}/accounts/{account_id}/contacts/{contact_id}"
    try:
        resp = client.put(
            url,
            headers=_headers_chatwoot(),
            json={"custom_attributes": {"crm_id": crm_id}},
            timeout=TIMEOUT,
        )
    except httpx.HTTPError as exc:
        print("❌ Chatwoot contact update error:", exc)
        return False

    if resp.status_code >= 300:
        print("❌ Chatwoot contact update failed:", resp.status_code, resp.text)
        return False

    print("✅ Chatwoot contact updated with crm_id:", crm_id)
    return True


def _extract_ids(data: Dict[str, Any], contact: Dict[str, Any]) -> Dict[str, Optional[int]]:
    account_id = contact.get("account_id") or (data.get("account") or {}).get("id")
    contact_id = contact.get("id") or data.get("id")

    if isinstance(account_id, str) and account_id.isdigit():
        account_id = int(account_id)
    if isinstance(contact_id, str) and contact_id.isdigit():
        contact_id = int(contact_id)

    return {"account_id": account_id, "contact_id": contact_id}


def handleContactCreated(data: Dict[str, Any]):
    contact = (data.get("contact") if isinstance(data, dict) else None) or data
    if not isinstance(contact, dict):
        print("⚠️ No contact payload to sync.")
        return

    payload = _extract_contact_payload(contact)
    if not payload.get("name") and not payload.get("emails"):
        print("⚠️ Skipping Twenty sync, insufficient data:", payload)
        return

    existing_crm_id = (
        (contact.get("custom_attributes") or {}).get("crm_id")
        or _clean(contact.get("crm_id"))
    )

    ids = _extract_ids(data, contact)
    chatwoot_id = ids["contact_id"]

    with httpx.Client() as client:
        crm_id = create_or_update_people(
            client,
            chatwoot_id=str(chatwoot_id) if chatwoot_id is not None else None,
            payload=payload,
            crm_id=existing_crm_id,
        )
        print("✅ Twenty CRM ID after upsert:", crm_id)
        updated = _sync_crm_id(
            client,
            account_id=ids["account_id"],
            contact_id=chatwoot_id,
            crm_id=crm_id,
        )
        if updated:
            contact.setdefault("custom_attributes", {})
            contact["custom_attributes"]["crm_id"] = crm_id
            print("🔁 Updated in-memory contact custom_attributes with crm_id.")
