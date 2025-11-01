# VD RAG Bot

Python FastAPI service that powers a retrieval-augmented assistant for Chatwoot and forwards CRM events to Twenty/n8n. The bot answers with OpenAI models, routes hand-offs to humans, and uses a local vector store built from your knowledge base files.

---

## 1. Requirements

- Docker and Docker Compose (latest)
- Python 3.11 if running locally (the repo uses [uv](https://docs.astral.sh/uv/) for dependency management)
- Chatwoot workspace with bot access
- OpenAI API key with access to the models you plan to use
- Optional: Twenty workspace & API key, n8n instance for workflow automation

---

## 2. Configuration

1. Copy the template env file and edit it with real secrets:

   ```bash
   cp .env.example .env
   ```

2. Populate the following variables:

   - `DATABASE_URL` – Postgres connection string (e.g. `postgresql+psycopg://user:pass@host:5432/db`)
   - `CHATWOOT_BOT_ACCESS_TOKEN` – bot token generated from Chatwoot Settings → Agents → Add bot
   - `CHATWOOT_API_ACCESS_TOKEN` – Personal Access Token from Chatwoot profile settings (used for outbound API calls)
   - `CHATWOOT_API_URL` – base URL to your Chatwoot API (defaults expect Docker Desktop sharing through `host.docker.internal`)
   - `TWENTY_API_KEY`, `TWENTY_BASE_URL` – required if you forward events to Twenty
   - `N8N_*` variables – base URLs for n8n webhooks if you rely on the provided workflows

3. (Optional) Point `KNOWLEDGE_FILE` and `RAG_PERSIST_DIR` to custom locations if you store documents outside the repo.

Chatwoot token quick reference:

1. **Create bot** → set the webhook to `http://host.docker.internal:8080/bot`, pick a name/icon, copy the generated token into `CHATWOOT_BOT_ACCESS_TOKEN`.
2. **Generate personal token** → click your avatar → Profile Settings → Create Personal Access Token → copy into `CHATWOOT_API_ACCESS_TOKEN`.

---

## 3. Running with Docker

```bash
docker compose up --build
```

- App service exposes FastAPI at http://localhost:8080
- n8n UI lives at http://localhost:5678 (credentials are disabled by default – add basic auth variables in `docker-compose.yml` for production)
- Code mounts into the container at `/workspace`; `uvicorn --reload` handles hot reloads

Inside the container you can open a shell that already has dependencies installed:

```bash
docker compose exec app bash
```

---

## 4. Local development without Docker

1. Ensure Python 3.11 and `uv` are available on your PATH.
2. Create the virtual env and install dependencies:

   ```bash
   uv sync --python 3.11
   ```

3. Run the API locally:

   ```bash
   uv run --python 3.11 --env-file .env uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
   ```

4. (Optional) Open an interactive shell inside the project environment:

   ```bash
   uv run --python 3.11 --env-file .env python
   ```

---

## 5. Knowledge base ingestion (RAG)

1. Drop markdown, HTML, or text files into `app/rag_engine/storage/` (subdirectories allowed).
2. Rebuild the vector index whenever documents change:

   ```bash
   uv run --python 3.11 --env-file .env rag-ingest
   ```

   If the CLI entry point is unavailable, run `uv run --python 3.11 --env-file .env python -m app.rag_engine.ingest`.

3. The command recreates `app/rag_engine/storage/vector_store/` with the latest embeddings. Restart the API to pick up changes.

---

## 6. Testing the bot webhook

- Point your Chatwoot bot webhook to `http://host.docker.internal:8080/bot` when running via Docker Desktop, or to `http://localhost:8080/bot` when running locally.
- Send an inbound message in Chatwoot; the bot will classify the intent, fetch relevant context from the vector store, and respond (or escalate).
- If you rely on n8n, confirm that recipients `http://host.docker.internal:5678/webhook/*` are reachable from the Chatwoot container.

---

## 7. Useful commands

- `uv run --python 3.11 --env-file .env pytest` – execute the Python test suite (add tests under `tests/`)
- `docker compose logs -f app` – follow FastAPI logs for debugging
- `docker compose down` – stop all services and remove containers

---

## 8. Troubleshooting

- **Authentication errors** – double-check the Chatwoot or OpenAI keys in `.env`; restart the container after editing env vars.
- **No knowledge base hits** – ensure you ran the ingest command and that `app/rag_engine/storage/vector_store/` exists with fresh data.
- **Timeouts to n8n** – confirm the `WEBHOOK_URL` matches the host that Chatwoot can reach (use ngrok/public URL for remote testing).

## 9. Bot usage metrics

- Each `/bot` request increments a per-tenant daily counter stored in the `bot_request_usage` table (created automatically on first use).
- Columns: `tenant_id`, `bucket_date`, `request_count`, `last_request_at`.
- The aggregated data can feed dashboards or downstream quota enforcement without additional code changes.
- Set `monthly_llm_request_limit` inside a tenant's `llm_params` to automatically stop LLM traffic once the monthly cap is hit; the webhook replies with `monthly_llm_limit_reached_reply` (or a default notice) when the limit triggers.

# Cloudflare Tunnel Quick Setup

This is a simplified guide to expose local apps using Cloudflare Tunnel.

## Steps

1. **Install `cloudflared`**

   ```bash
   brew install cloudflare/cloudflare/cloudflared
   cloudflared --version
   ```

2. **Login to Cloudflare**

   ```bash
   cloudflared tunnel login
   ```

   → Opens browser → select your Cloudflare account and domain.

3. **Create a Tunnel**

   ```bash
   cloudflared tunnel create prod
   ```

   This outputs a `TUNNEL_UUID` and creates a JSON credentials file in `~/.cloudflared/`.

4. **Create Config File**
   Save as `~/.cloudflared/config.yml`:

   ```yaml
   tunnel: <TUNNEL_UUID>
   credentials-file: /Users/<user>/.cloudflared/<TUNNEL_UUID>.json

   ingress:
     - hostname: vdbot.veridatapro.com
       service: http://localhost:8080

     - hostname: chatwoot.veridatapro.com
       service: http://localhost:3000

     - service: http_status:404
   ```

5. **Map DNS**

   ```bash
   cloudflared tunnel route dns <TUNNEL_UUID> vdbot.veridatapro.com
   cloudflared tunnel route dns <TUNNEL_UUID> chatwoot.veridatapro.com
   ```

6. **Run the Tunnel**

   ```bash
   cloudflared tunnel run <TUNNEL_UUID>
   ```

7. **(Optional) Install as Service**
   ```bash
   sudo cloudflared service install
   ```

## Notes

- Keep your apps bound to `localhost`.
- No need to open ports 80/443.
- Use two connectors for HA in production.
- Free plan limits: 1,000 tunnels, 1,000 routes per tunnel, 25 connectors, 100 MB upload/request.
