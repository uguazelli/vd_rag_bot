from __future__ import annotations
import os
from typing import Any, Dict, Optional

from app.services.repo import (
    create_contact,
    get_contact_by_phone_or_email,
    update_contact,
)
from app.twenty.people import create_people, get_people_by_email_or_phone, update_people

TWENTY_BASE_URL = os.getenv("TWENTY_BASE_URL")
TWENTY_API_KEY= os.getenv("TWENTY_API_KEY")

def _split_name(raw: Optional[str], fallback: str = "Chatwoot Contact") -> tuple[str, str]:
    s = (raw or "").strip()
    if not s:
        return fallback, ""
    parts = [p for p in s.split() if p]
    if len(parts) == 1:
        return parts[0], ""
    return " ".join(parts[:-1]), parts[-1]


def handleContact(data: Dict[str, Any]) -> None:
    # 0) Ignore non-contact events
    event = data.get("event") or ""
    if not event.startswith("contact_"):
        return

    account = data.get("account") or {}


    # 2) Safe nested dicts
    addl = data.get("additional_attributes") or {}
    cust = data.get("custom_attributes") or {}

    # 3) Compute names once
    first_name, last_name = _split_name(
        data.get("name"),
        fallback=(data.get("identifier") or "Chatwoot Contact"),
    )


    # 5) Look up in Twenty by email/phone
    result = get_people_by_email_or_phone(
        base_url=TWENTY_BASE_URL,
        email=data.get("email"),
        raw_phone=data.get("phone_number"),
        token=TWENTY_API_KEY,
    )
    if not result:
        return

    # print("🤖 VD Twenty people:", result)
    total = result.get("totalCount", 0) or 0
    person_id = result.get("data").get("people")[0].get("id")

    # 6a) Create in Twenty, then link back locally
    if total == 0:
        # print("🤖 Creating a new person in Twenty")
        created = create_people(
            base_url=TWENTY_BASE_URL,
            token=TWENTY_API_KEY,
            first_name=first_name,
            last_name=last_name,
            email=data.get("email"),
            raw_phone=data.get("phone_number"),
            city=addl.get("city"),
            company_id=cust.get("company_id"),
        )
        # Robustly extract the new Twenty ID
        new_pid = None
        if isinstance(created, dict):
            # common REST shape: {"data": {"createPerson": {"id": "...", ...}}}
            data_block = created.get("data") or {}
            maybe_create = data_block.get("createPerson") or data_block.get("person") or {}
            new_pid = maybe_create.get("id") or created.get("id")

        if new_pid and local_contact_id is not None:
            # Link back to local
            update_contact(
                contact_id=local_contact_id,
                twenty_person_id=new_pid,
                first_name=first_name,
                last_name=last_name,
                email=data.get("email"),
                phone=data.get("phone_number"),
                city=addl.get("city"),
                linkedin_url=addl.get("linkedin_url"),
                facebook_url=addl.get("facebook_url"),
                instagram_url=addl.get("instagram_url"),
                github_url=addl.get("github_url"),
                x_url=addl.get("x_url"),
                company_id=cust.get("company_id"),
                chatwoot_contact_id=data.get("id"),
            )

    # 6b) Update in Twenty (matched)
    if total > 0:

        if not person_id:
            # Fallback: nothing to update
            print("⚠️ Twenty search returned results but no person id could be extracted.")
            return

        # print("🤖 Updating an existing person in Twenty:", person_id)
        update_people(
            base_url=TWENTY_BASE_URL,
            token=TWENTY_API_KEY,
            person_id=person_id,
            first_name=first_name,
            last_name=last_name,
            email=data.get("email"),
            raw_phone=data.get("phone_number"),
            city=addl.get("city"),
            company_id=cust.get("company_id"),
        )


    # 4) Local lookup
    contact = get_contact_by_phone_or_email(
        phone=data.get("phone_number"),
        email=data.get("email"),
    )

    local_contact_id: Optional[int] = None
    if contact:
        local_contact_id = contact["id"]
        # Update local contact
        update_contact(
            contact_id=local_contact_id,
            first_name=first_name,
            last_name=last_name,
            email=data.get("email"),
            phone=data.get("phone_number"),
            city=addl.get("city"),
            linkedin_url=addl.get("linkedin_url"),
            facebook_url=addl.get("facebook_url"),
            instagram_url=addl.get("instagram_url"),
            github_url=addl.get("github_url"),
            x_url=addl.get("x_url"),
            company_id=cust.get("company_id"),
            chatwoot_contact_id=data.get("id"),
            twenty_person_id=person_id,
        )
    else:
        # Create local contact (capture ID!)
        local_contact_id = create_contact(
            tenant_id="",
            first_name=first_name,
            last_name=last_name,
            email=data.get("email"),
            phone=data.get("phone_number"),
            city=addl.get("city"),
            linkedin_url=addl.get("linkedin_url"),
            facebook_url=addl.get("facebook_url"),
            instagram_url=addl.get("instagram_url"),
            github_url=addl.get("github_url"),
            x_url=addl.get("x_url"),
            company_id=cust.get("company_id"),
            chatwoot_contact_id=data.get("id"),
            twenty_person_id=person_id,
        )
