import os
import re
import httpx

TWENTY_API_KEY = os.getenv("TWENTY_API_KEY")
TWENTY_BASE_URL = os.getenv("TWENTY_BASE_URL", "http://localhost:8000")

def handleContactCreated(data):
    name = (data.get("name") or "").strip()
    parts = re.split(r"\s+", name) if name else []
    first_name = parts[0] if parts else None
    last_name = " ".join(parts[1:]) if len(parts) > 1 else None

    email = (data.get("email") or "").strip() or None
    phone = (data.get("phone_number") or "").strip() or None

    add = data.get("additional_attributes") or {}
    social = add.get("social_profiles") or {}
    linkedin_url = (social.get("linkedin") or "").strip() or None
    x_url = (social.get("twitter") or "").strip() or None
    city = (add.get("city") or "").strip() or None

    # Build minimal payload, only include keys that have values
    payload = {"createdBy": {"source": "API"}}

    if first_name or last_name:
        payload["name"] = {}
        if first_name: payload["name"]["firstName"] = first_name
        if last_name:  payload["name"]["lastName"] = last_name

    if email:
        payload["emails"] = {"primaryEmail": email}

    if linkedin_url:
        payload["linkedinLink"] = {"primaryLinkUrl": linkedin_url}

    if x_url:
        payload["xLink"] = {"primaryLinkUrl": x_url}

    if phone:
        payload["phones"] = {"primaryPhoneNumber": phone}

    if city:
        payload["city"] = city

    headers = {
        "Authorization": f"Bearer {TWENTY_API_KEY}",
        "Accept": "application/json",
    }

    people_id = "b05dc070-dd16-4ee9-bea0-ef8b6711b893"
    url = f"{TWENTY_BASE_URL.rstrip('/')}/rest/people/{people_id}"
    params = {"depth": 1}

    with httpx.Client(timeout=10.0) as client:
        r = client.patch(url, params=params, json=payload, headers=headers)
        if r.status_code >= 400:
            print("PATCH failed:", r.status_code, r.text)
            return {"status": r.status_code, "error": r.text, "sent": payload}
        body = r.json() if r.headers.get("content-type","").startswith("application/json") and r.content else None
        print("Status:", r.status_code)
        print("Body:", body)
        return {"status": r.status_code, "body": body, "sent": payload}
