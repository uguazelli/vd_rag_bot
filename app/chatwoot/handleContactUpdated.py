import os
import re
from typing import Any, Dict, Optional

import httpx

from app.twenty import upsert_contact

CHATWOOT_API_URL = os.getenv("CHATWOOT_API_URL", "http://localhost:3000/api/v1")
CHATWOOT_BOT_TOKEN = os.getenv("BOT_ACCESS_TOKEN", "nS7yBjTg66L29cSUVypLQnGB")


def _headers_chatwoot() -> Dict[str, str]:
    return {
        "Content-Type": "application/json",
        "api_access_token": CHATWOOT_BOT_TOKEN,
    }


def _clean(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _extract_contact_payload(contact: Dict[str, Any]) -> Dict[str, Any]:
    print("🔍 Extracting payload from contact:", contact)
    name = _clean(contact.get("name"))
    parts = re.split(r"\s+", name) if name else []
    first_name = parts[0] if parts else None
    last_name = " ".join(parts[1:]) if len(parts) > 1 else None

    email = _clean(contact.get("email"))
    phone = _clean(contact.get("phone_number"))

    add = contact.get("additional_attributes") or {}
    social = add.get("social_profiles") or {}
    linkedin_url = _clean(social.get("linkedin"))
    x_url = _clean(social.get("twitter"))
    city = _clean(add.get("city"))

    payload: Dict[str, Any] = {"createdBy": {"source": "API"}}
    if first_name or last_name:
        payload["name"] = {}
        if first_name:
            payload["name"]["firstName"] = first_name
        if last_name:
            payload["name"]["lastName"] = last_name
    if email:
        payload["emails"] = {"primaryEmail": email}
    if phone:
        payload["phones"] = {"primaryPhoneNumber": phone}
    if linkedin_url:
        payload["linkedinLink"] = {"primaryLinkUrl": linkedin_url}
    if x_url:
        payload["xLink"] = {"primaryLinkUrl": x_url}
    if city:
        payload["city"] = city
    return payload


def _update_chatwoot_crm_id(
    client: httpx.Client,
    *,
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

    url = (
        f"{CHATWOOT_API_URL.rstrip('/')}"
        f"/accounts/{account_id}/contacts/{contact_id}"
    )
    try:
        print(
            "📡 Updating Chatwoot contact:",
            {"url": url, "crm_id": crm_id, "account_id": account_id, "contact_id": contact_id},
        )
        resp = client.put(
            url,
            headers=_headers_chatwoot(),
            json={"custom_attributes": {"crm_id": crm_id}},
            timeout=10.0,
        )
        print("📥 Chatwoot response:", resp.status_code, resp.text)
        if resp.status_code >= 300:
            print("❌ Chatwoot contact update failed:", resp.status_code, resp.text)
            return False
        print("✅ Chatwoot contact updated with crm_id:", crm_id)
        return True
    except httpx.HTTPError as exc:
        print("❌ Chatwoot contact update error:", exc)
        return False


def handleContactCreated(data: Dict[str, Any]):
    print("🚀 handleContactCreated invoked with:", data)
    contact = data.get("contact") or data
    if not isinstance(contact, dict):
        print("⚠️ No contact payload to sync.")
        return

    custom = contact.get("custom_attributes") or {}
    existing_crm_id = custom.get("crm_id") or _clean(contact.get("crm_id"))

    payload = _extract_contact_payload(contact)
    if not payload.get("name") and not payload.get("emails"):
        print("⚠️ Skipping Twenty sync, insufficient data:", payload)
        return

    account_id = (
        contact.get("account_id")
        or (data.get("account") or {}).get("id")
    )
    contact_id = contact.get("id") or data.get("id")
    if isinstance(account_id, str) and account_id.isdigit():
        account_id = int(account_id)
    if isinstance(contact_id, str) and contact_id.isdigit():
        contact_id = int(contact_id)

    with httpx.Client() as client:
        crm_id = upsert_contact(client, payload, crm_id=existing_crm_id)
        print("✅ Twenty CRM ID after upsert:", crm_id)
        updated = _update_chatwoot_crm_id(
            client,
            account_id=account_id,
            contact_id=contact_id,
            crm_id=crm_id,
        )
        if updated and isinstance(contact, dict):
            contact.setdefault("custom_attributes", {})
            contact["custom_attributes"]["crm_id"] = crm_id
            print("🔁 Updated in-memory contact custom_attributes with crm_id.")
