from typing import Dict, Optional
import httpx
from app.config import settings
from app.twenty.people import create_or_update_people

CHATWOOT_API_URL = settings.chatwoot_api_url.rstrip("/")
CHATWOOT_BOT_TOKEN = settings.chatwoot_bot_access_token or ""
TIMEOUT = 10.0


def handleContactCreated(data: Dict):
    contact = data.get("contact") or data
    if not isinstance(contact, dict):
        return

    def pick(value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        return value or None

    additional = contact.get("additional_attributes") or {}
    social = additional.get("social_profiles") or {}

    payload: Dict[str, Dict] = {"createdBy": {"source": "API"}}

    name_tokens = (contact.get("name") or "").strip().split()
    if name_tokens:
        payload["name"] = {"firstName": name_tokens[0]}
        if len(name_tokens) > 1:
            payload["name"]["lastName"] = " ".join(name_tokens[1:])

    email = pick(contact.get("email"))
    if email:
        payload["emails"] = {"primaryEmail": email}

    phone = pick(contact.get("phone_number"))
    if phone:
        payload["phones"] = {"primaryPhoneNumber": phone}

    linkedin = pick(social.get("linkedin"))
    if linkedin:
        payload["linkedinLink"] = {"primaryLinkUrl": linkedin}

    twitter = pick(social.get("twitter"))
    if twitter:
        payload["xLink"] = {"primaryLinkUrl": twitter}

    city = pick(additional.get("city"))
    if city:
        payload["city"] = city

    custom_attrs = contact.get("custom_attributes") or {}
    existing_crm_id = pick(custom_attrs.get("crm_id") or contact.get("crm_id"))

    account_id = contact.get("account_id") or (data.get("account") or {}).get("id")
    contact_id = contact.get("id") or data.get("id")

    with httpx.Client() as client:
        crm_id = create_or_update_people(
            client,
            chatwoot_id=str(contact_id) if contact_id is not None else None,
            payload=payload,
            crm_id=existing_crm_id,
        )

        if not crm_id or not account_id or contact_id is None:
            return

        client.put(
            f"{CHATWOOT_API_URL}/accounts/{account_id}/contacts/{contact_id}",
            headers={"Content-Type": "application/json", "api_access_token": CHATWOOT_BOT_TOKEN},
            json={"custom_attributes": {"crm_id": crm_id}},
            timeout=TIMEOUT,
        )
        contact.setdefault("custom_attributes", {})
        contact["custom_attributes"]["crm_id"] = crm_id
