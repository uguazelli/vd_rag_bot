"""Raw SQL statements used by the application.

Keeping queries in their own module keeps repository functions concise and
makes it easy to share statements between different call sites.
"""

SQL_GET_PARAMS_BY_OMNICHANNEL_ID = """
SELECT
  t.id, t.email,
  l.id as llm_id, l.name as llm_name, l.api_key as llm_api_key, l.params as llm_params,
  c.id as crm_id, c.url as crm_url, c.api_key as crm_api_key, c.params as crm_params,
  o.id as omnichannel_id, o.params as omnichannel
FROM tenants AS t
JOIN llm         AS l ON l.tenant_id = t.id
JOIN crm         AS c ON c.tenant_id = t.id
JOIN omnichannel AS o ON o.tenant_id = t.id
WHERE o.id = %(omnichannel_id)s
"""


SQL_GET_PARAMS_BY_TENANT_ID = """
SELECT
  t.id, t.email,
  l.id as llm_id, l.name as llm_name, l.api_key as llm_api_key, l.params as llm_params,
  c.id as crm_id, c.url as crm_url, c.api_key as crm_api_key, c.params as crm_params,
  o.id as omnichannel_id, o.params as omnichannel
FROM tenants AS t
JOIN llm         AS l ON l.tenant_id = t.id
JOIN crm         AS c ON c.tenant_id = t.id
JOIN omnichannel AS o ON o.tenant_id = t.id
WHERE t.id = %(tenant_id)s
"""

