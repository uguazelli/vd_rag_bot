from __future__ import annotations
from typing import Optional, Dict, Any, List
import requests
import re

TIMEOUT = 10.0

# Minimal calling code -> ISO country mapping (extend as needed)
CALLING_TO_COUNTRY = {
    "1": "US",    # also CA etc., but US is fine as a default for +1
    "33": "FR",
    "34": "ES",
    "39": "IT",
    "44": "GB",
    "49": "DE",
    "51": "PE",
    "52": "MX",
    "54": "AR",
    "55": "BR",
    "56": "CL",
    "57": "CO",
    "58": "VE",
    "351": "PT",
    "595": "PY",
    "598": "UY",
}


def _split_e164(raw: str) -> tuple[str | None, str | None, str | None]:
    """
    Split a raw E.164-ish string like '+595981272934' into:
      (calling_code_with_plus, national_number, country_code_iso2)
    Returns (None, None, None) if it can't parse anything sensible.
    """
    if not raw:
        return None, None, None

    # keep only + and digits, strip whitespace
    s = re.sub(r"[^\d+]", "", raw.strip())

    if not s:
        return None, None, None

    if s[0] != "+":
        # No + present; treat as local number
        return None, s, None

    digits = s[1:]
    if not digits:
        return None, None, None

    # Try longest-first match for calling code (3, then 2, then 1)
    for klen in (3, 2, 1):
        if len(digits) >= klen:
            code = digits[:klen]
            rest = digits[klen:]
            if code in CALLING_TO_COUNTRY or klen in (3, 2, 1):
                # Prefer known mapping; if unknown, still accept as calling code
                country = CALLING_TO_COUNTRY.get(code)
                calling = f"+{code}"
                national = rest
                # Fallback: if we picked an unknown 3/2/1 and national is empty, bail
                if not national:
                    return calling, None, country
                return calling, national, country

    return None, None, None


def _make_filter(email: Optional[str], raw_phone: Optional[str]) -> str:
    parts: List[str] = []
    if email:
        parts.append(f'emails.primaryEmail[eq]:"{email}"')
    if raw_phone:
        calling, national, _ = _split_e164(raw_phone)
        if national and calling:
            parts.append(
                f'and(phones.primaryPhoneNumber[eq]:"{national}",'
                f'phones.primaryPhoneCallingCode[eq]:"{calling}")'
            )
        elif national:
            parts.append(f'phones.primaryPhoneNumber[eq]:"{national}"')
        else:
            # Fallback: try exact match on whatever was provided
            parts.append(f'phones.primaryPhoneNumber[eq]:"{raw_phone}"')
    if not parts:
        raise ValueError("At least one of email or phone must be provided")
    return parts[0] if len(parts) == 1 else f'or({",".join(parts)})'


# def _make_filter(email: Optional[str], phone: Optional[str]) -> str:
#     parts = []
#     if email:
#         parts.append(f'emails.primaryEmail[eq]:"{email}"')
#     if phone:
#         parts.append(f'phones.primaryPhoneNumber[eq]:"{phone}"')
#     if not parts:
#         raise ValueError("At least one of email or phone must be provided")
#     return parts[0] if len(parts) == 1 else f'or({",".join(parts)})'


def get_people_by_email_or_phone(
    *,
    base_url: str,
    email: Optional[str],
    raw_phone: Optional[str],
    token: str,
    timeout: float = 10.0,
) -> Dict:
    url = f"{base_url.rstrip('/')}/rest/people"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
    }
    params = {
        "order_by": "createdAt",
        "filter": _make_filter(email, raw_phone),
    }
    r = requests.get(url, headers=headers, params=params, timeout=timeout)
    r.raise_for_status()
    return r.json()


def create_people(
    *,
    base_url: str,
    token: str,
    first_name: str | None = None,
    last_name: str | None = None,
    email: str | None = None,
    raw_phone: str | None = None,          # e.g. "+595981272934"
    city: str | None = None,
    company_id: str | None = None,         # UUID
    depth: int = 1,
    timeout: float = 10.0,
):
    """
    POST /rest/people using a minimal payload.
    - raw_phone like '+595981272934' is split into calling code + national number.
    - If country can't be inferred, it is omitted (calling code + number still sent).
    """
    url = f"{base_url.rstrip('/')}/rest/people"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    body = {}

    if company_id is not None:
        body["companyId"] = company_id
    if city is not None:
        body["city"] = city

    name = {}
    if first_name:
        name["firstName"] = first_name
    if last_name:
        name["lastName"] = last_name
    if name:
        body["name"] = name

    if email is not None:
        body["emails"] = {"primaryEmail": email}

    if raw_phone:
        calling, national, iso2 = _split_e164(raw_phone)
        phones = {}
        if national:
            phones["primaryPhoneNumber"] = national
        if calling:
            phones["primaryPhoneCallingCode"] = calling
        if iso2:
            phones["primaryPhoneCountryCode"] = iso2
        if phones:
            body["phones"] = phones

    r = requests.post(url, headers=headers, params={"depth": depth}, json=body, timeout=timeout)
    r.raise_for_status()  # expect 201
    return r.json()


def update_people(
    *,
    base_url: str,
    token: str,
    person_id: str,
    depth: int = 1,
    timeout: float = 10.0,

    # Top-level simple fields
    company_id: Optional[str] = None,
    city: Optional[str] = None,
    # Name
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    # Email (primary)
    email: Optional[str] = None,
    # Phones: pass raw like '+595981981981' (E.164)
    raw_phone: Optional[str] = None,
    # Links (LinkedIn / X)
    linkedin_url: Optional[str] = None,
    x_url: Optional[str] = None,
) -> Dict[str, Any]:

    url = f"{base_url.rstrip('/')}/rest/people/{person_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    params = {"depth": depth}

    body: Dict[str, Any] = {}

    if company_id:
        body["companyId"] = company_id
    if city:
        body["city"] = city

    # name (avoid empty strings)
    name = {}
    if first_name:
        name["firstName"] = first_name
    if last_name:
        name["lastName"] = last_name
    if name:
        body["name"] = name

    # emails (avoid sending empty string)
    if email:
        body["emails"] = {"primaryEmail": email}

    # phones (normalize from raw E.164 like "+595981981981")
    if raw_phone:
        calling, national, iso2 = _split_e164(raw_phone)
        phones: Dict[str, Any] = {}
        if national:
            phones["primaryPhoneNumber"] = national
        if calling:
            phones["primaryPhoneCallingCode"] = calling
        if iso2:
            phones["primaryPhoneCountryCode"] = iso2
        if phones:
            body["phones"] = phones

    # linkedin
    if linkedin_url:
        body["linkedinLink"] = {"primaryLinkUrl": linkedin_url}

    # X / Twitter
    if x_url:
        body["xLink"] = {"primaryLinkUrl": x_url}

    if not body:
        raise ValueError("No fields provided to update.")

    r = requests.patch(url, headers=headers, params=params, json=body, timeout=timeout)
    try:
        r.raise_for_status()  # expect 200
    except requests.HTTPError as e:
        # surface server message to help debug bad requests
        raise requests.HTTPError(f"{e} | Response: {r.text}") from e
    return r.json()

