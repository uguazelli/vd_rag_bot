from typing import Any, Dict
import json
import httpx
from app.config import settings
from app.twenty.people import create_or_update_people

CHATWOOT_API_URL = settings.chatwoot_api_url.rstrip("/")
CHATWOOT_BOT_TOKEN = settings.chatwoot_bot_access_token
TIMEOUT = 10.0


def _ensure_dict(value: Any) -> Dict:
    return value if isinstance(value, dict) else {}


def _strip_nulls(value: Any) -> Any:
    if isinstance(value, dict):
        cleaned = {}
        for key, val in value.items():
            filtered = _strip_nulls(val)
            if filtered not in (None, {}, []):
                cleaned[key] = filtered
        return cleaned
    if isinstance(value, list):
        cleaned_list = [_strip_nulls(item) for item in value]
        return [item for item in cleaned_list if item not in (None, {}, [])]
    return value


def handleContactCreated(data: Dict):
    event = data.get("event") or ""
    payload = _ensure_dict(data.get("payload"))

    contact: Dict[str, Any] = {}
    contact_id = None
    account_id = (data.get("account") or {}).get("id")

    if event.startswith("message_"):
        conversation = _ensure_dict(data.get("conversation"))
        contact_id = (conversation.get("contact_inbox") or {}).get("contact_id")

        messages = conversation.get("messages") or []
        last_message = messages[-1] if messages else {}
        sender = _ensure_dict(last_message.get("sender") or data.get("sender"))

        if not contact_id:
            contact_id = sender.get("id")

        contact = sender
    elif event.startswith("contact_") or not event:
        contact = _ensure_dict(payload.get("contact") if "contact" in payload else payload or data)
        contact_id = contact.get("id")
        account_id = account_id or contact.get("account_id")
    else:
        return

    if not contact_id or not isinstance(contact, dict):
        return

    additional = _ensure_dict(contact.get("additional_attributes"))
    social = _ensure_dict(additional.get("social_profiles"))

    raw_full_name = contact.get("name") or ""
    parts = [p for p in raw_full_name.strip().split() if p]
    if len(parts) > 1:
        first_name = " ".join(parts[:-1])
        last_name = parts[-1]
    elif len(parts) == 1:
        first_name = parts[0]
        last_name = ""
    else:
        identifier = contact.get("identifier") or "Chatwoot Contact"
        first_name = identifier
        last_name = ""

    payload_for_twenty = {
        "createdBy": {"source": "API"},
        "name": {
            "firstName": first_name,
            "lastName": last_name,
        },
        "emails": {"primaryEmail": contact.get("email")},
        "phones": {"primaryPhoneNumber": contact.get("phone_number")},
        "linkedinLink": {"primaryLinkUrl": social.get("linkedin")},
        "xLink": {"primaryLinkUrl": social.get("twitter")},
        "city": additional.get("city"),
    }

    payload_for_twenty = _strip_nulls(payload_for_twenty)
    if "name" not in payload_for_twenty or "firstName" not in payload_for_twenty["name"]:
        payload_for_twenty["name"] = {
            "firstName": contact.get("name")
            or contact.get("identifier")
            or "Chatwoot Contact"
        }

    crm_id = (contact.get("custom_attributes") or {}).get("crm_id") or contact.get("crm_id")

    with httpx.Client() as client:
        print("➡️ Twenty upsert payload:", json.dumps(payload_for_twenty, ensure_ascii=False))
        new_crm_id = create_or_update_people(
            client=client,
            chatwoot_id=str(contact_id),
            payload=payload_for_twenty,
            crm_id=crm_id,
        )

        if not new_crm_id or not account_id:
            return

        print(
            "↩️ Syncing CRM ID back to Chatwoot:",
            {"account_id": account_id, "contact_id": contact_id, "crm_id": new_crm_id},
        )
        client.put(
            f"{CHATWOOT_API_URL}/accounts/{account_id}/contacts/{contact_id}",
            headers={
                "Content-Type": "application/json",
                "api_access_token": CHATWOOT_BOT_TOKEN,
            },
            json={"custom_attributes": {"crm_id": new_crm_id}},
            timeout=TIMEOUT,
        )

        contact.setdefault("custom_attributes", {})
        contact["custom_attributes"]["crm_id"] = new_crm_id
