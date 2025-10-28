INSERT INTO public.llm(
	tenant_id, name, api_key, params)
	VALUES ( 1,
	'openai',
	'xxx',
	'{
	"model_answer": "gpt-4o-mini"
	}');


INSERT INTO public.llm(
	tenant_id, name, api_key, params)
	VALUES (
	1,
	'openai',
	'apikey',
	'{
	    "top_k": 4,
	    "temperature": 0.2,
	    "model_answer": "gpt-4o-mini",
	    "handoff_priority": "high",
	    "openai_embed_model": "text-embedding-3-small",
	    "handoff_private_note": "Bot routed the conversation for human follow-up.",
	    "handoff_public_reply": "Ok, please hold on while I connect you with a human agent.",
	    "rag_cross_encoder_model": "cross-encoder/ms-marco-MiniLM-L-6-v2"
	}'::jsonb
	);


INSERT INTO public.omnichannel(
	 tenant_id, crm_id, params)
	VALUES (1, '1', '{
    "chatwoot_bot_access_token":"xxx",
    "chatwoot_api_access_token":"xxx",
    "chatwoot_api_url":"http://host.docker.internal:3000/api/v1",
    "chatwoot_account_id":"2"
}'::jsonb);



INSERT INTO public.crm(
	tenant_id, url, api_key, params)
	VALUES (
	1,
	'http://host.docker.internal:8000',
	'xxx',
	'{}');


SELECT jsonb_pretty(params) FROM llm;