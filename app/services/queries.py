# Tenants
SQL_GET_TENANT_BY_CHATWOOT = """
SELECT *
FROM tenants
WHERE chatwoot_account_id = %(account_id)s
"""

# Contacts – lookups
SQL_GET_CONTACT_BY_PHONE_OR_EMAIL = """
SELECT *
FROM contacts
WHERE phone = %(phone)s OR LOWER(email) = LOWER(%(email)s)
LIMIT 1
"""

# Update every editable column by id (named params)
SQL_UPDATE_CONTACT_FULL = """
UPDATE contacts
SET
  first_name = %(first_name)s,
  last_name = %(last_name)s,
  email = %(email)s,
  phone = %(phone)s,
  city = %(city)s,
  linkedin_url = %(linkedin_url)s,
  facebook_url = %(facebook_url)s,
  instagram_url = %(instagram_url)s,
  github_url = %(github_url)s,
  x_url = %(x_url)s,
  company_id = %(company_id)s,
  chatwoot_contact_id = %(chatwoot_contact_id)s,
  twenty_person_id = %(twenty_person_id)s,
  updated_at = NOW()
WHERE id = %(contact_id)s
"""

SQL_CREATE_CONTACT = """
INSERT INTO contacts (
  tenant_id,
  first_name,
  last_name,
  email,
  phone,
  city,
  job_title,
  linkedin_url,
  facebook_url,
  instagram_url,
  github_url,
  x_url,
  company_id,
  chatwoot_contact_id,
  twenty_person_id,
  created_at,
  updated_at
) VALUES (
  %(tenant_id)s,
  %(first_name)s,
  %(last_name)s,
  %(email)s,
  %(phone)s,
  %(city)s,
  %(job_title)s,
  %(linkedin_url)s,
  %(facebook_url)s,
  %(instagram_url)s,
  %(github_url)s,
  %(x_url)s,
  %(company_id)s,
  %(chatwoot_contact_id)s,
  %(twenty_person_id)s,
  NOW(),
  NOW()
)
RETURNING id
"""
