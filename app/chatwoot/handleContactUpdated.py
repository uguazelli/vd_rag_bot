from typing import Dict, Optional
import httpx
from app.config import settings
from app.twenty.people import create_or_update_people

CHATWOOT_API_URL = settings.chatwoot_api_url.rstrip("/")
CHATWOOT_BOT_TOKEN = settings.chatwoot_bot_access_token or ""
TIMEOUT = 10.0


def handleContactCreated(data: Dict):
    print("🤖 Contact created:", data)
    event = data.get("event") or ""
    if event.startswith("message_"):
        return

    payload_wrapper = data.get("payload")
    if isinstance(payload_wrapper, dict):
        contact_candidate = payload_wrapper.get("contact")
        contact = contact_candidate if isinstance(contact_candidate, dict) else payload_wrapper
    else:
        contact = data.get("contact")
        if not isinstance(contact, dict):
            contact = data
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

    first_hint = pick(additional.get("first_name") or additional.get("firstname"))
    last_hint = pick(additional.get("last_name") or additional.get("lastname"))

    raw_name = pick(contact.get("name"))
    name_tokens = raw_name.split() if raw_name else []

    phone = pick(contact.get("phone_number"))
    email = pick(contact.get("email"))

    if first_hint or last_hint:
        payload["name"] = {}
        if first_hint:
            payload["name"]["firstName"] = first_hint
        if last_hint:
            payload["name"]["lastName"] = last_hint
    elif name_tokens:
        payload["name"] = {"firstName": name_tokens[0]}
        if len(name_tokens) > 1:
            payload["name"]["lastName"] = " ".join(name_tokens[1:])
    else:
        fallback = phone or (email.split("@")[0] if email else None) or "Chatwoot Contact"
        payload["name"] = {"firstName": fallback}

    if email:
        payload["emails"] = {"primaryEmail": email}

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
    if contact_id is None:
        return

    with httpx.Client() as client:
        crm_id = create_or_update_people(
            client,
            chatwoot_id=str(contact_id),
            payload=payload,
            crm_id=existing_crm_id,
        )

        if not crm_id or not account_id:
            return

        client.put(
            f"{CHATWOOT_API_URL}/accounts/{account_id}/contacts/{contact_id}",
            headers={"Content-Type": "application/json", "api_access_token": CHATWOOT_BOT_TOKEN},
            json={"custom_attributes": {"crm_id": crm_id}},
            timeout=TIMEOUT,
        )
        contact.setdefault("custom_attributes", {})
        contact["custom_attributes"]["crm_id"] = crm_id
