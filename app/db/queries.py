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


SQL_CREATE_BOT_USAGE_TABLE = """
CREATE TABLE IF NOT EXISTS bot_request_usage (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL REFERENCES tenants(id),
    bucket_date DATE NOT NULL,
    request_count BIGINT NOT NULL DEFAULT 0,
    last_request_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, bucket_date)
);
"""


SQL_GET_BOT_REQUEST_COUNT_IN_RANGE = """
SELECT COALESCE(SUM(request_count), 0) AS total
FROM bot_request_usage
WHERE tenant_id = %(tenant_id)s
  AND bucket_date BETWEEN %(start_date)s AND %(end_date)s;
"""


SQL_INCREMENT_BOT_REQUEST_COUNT = """
INSERT INTO bot_request_usage (tenant_id, bucket_date, request_count, last_request_at)
VALUES (%(tenant_id)s, %(bucket_date)s, 1, NOW())
ON CONFLICT (tenant_id, bucket_date)
DO UPDATE SET
    request_count = bot_request_usage.request_count + 1,
    last_request_at = EXCLUDED.last_request_at
RETURNING request_count;
"""
