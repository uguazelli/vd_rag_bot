# VD RAG Bot

FastAPI service that powers retrieval-augmented replies inside Chatwoot conversations and can synchronise contact data with Twenty CRM. This project relies on OpenAI models, a PostgreSQL database, and knowledge base files configured through environment variables.

## Configuration

1. Copy the sample environment variables:
   ```bash
   cp .env.example .env
   ```
2. Update `.env` with:
   - `OPENAI_API_KEY` and preferred model names for answers and search queries.
   - `CHATWOOT_BOT_ACCESS_TOKEN` and `CHATWOOT_API_URL` so the bot can post messages back to Chatwoot.
   - `TWENTY_BASE_URL` and `TWENTY_API_KEY` if you want contact syncing with Twenty. (The workspace id is read from the database; no env var needed.)
   - Database credentials if you override the defaults supplied in `docker-compose.yml`.
3. When the FastAPI app starts it automatically executes `init_db()` (see `app/main.py`), which issues `CREATE TABLE IF NOT EXISTS` statements. No extra migration command is required, but ensure the database referenced by `DATABASE_URL` is reachable before booting the app. Both `postgresql://` and `postgresql+psycopg://` style URLs are accepted.

4. Seed the `tenants` table with at least one row so webhooks can be routed to the right credentials. For example:

   ```sql
   INSERT INTO public.tenants(
   name, chatwoot_account_id, chatwoot_api_url, chatwoot_bot_token, twenty_workspace_id, twenty_api_key, twenty_base_url)
   VALUES ('Veri Data',
   1,
   'http://host.docker.internal:3000/api/v1',
   'zdJTabnYrPQKRK8s7cwVYLso',
   'aec1a00b-ab4d-4109-85b2-f8bd0718401e',
   'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJjZTA1MDVjOS1jZWI2LTQ2ZTQtYjk4Ni0xOTRhY2Q3OTU4ODYiLCJ0eXBlIjoiQVBJX0tFWSIsIndvcmtzcGFjZUlkIjoiY2UwNTA1YzktY2ViNi00NmU0LWI5ODYtMTk0YWNkNzk1ODg2IiwiaWF0IjoxNzYwMDQ3NzMxLCJleHAiOjQ5MTM2NDc3MzAsImp0aSI6IjhmNjJiZDc4LTY2OWMtNGE5Yi04Njk2LTE2OWIxMzA1MzUzNyJ9.tyc2KW7a10pCopjy_QaH8m5tOnXqeHLb7OGzWHNM66A',
   'http://host.docker.internal:8000' );

   ```

   Add one row per customer/tenant with their Chatwoot and Twenty credentials.

If you had an earlier database without the newer columns, add them manually:

## Running with Docker

```bash
docker compose up --build
```

The API will be available on http://localhost:8080. Containers include the FastAPI app (`app`) and PostgreSQL (`db`).

### Coding inside the container

- Open a shell with all dependencies installed:
  ```bash
  docker compose exec app bash
  ```
- The image ships with the `uv` Python tool, so you can run local commands such as `uv run uvicorn app.main:app --reload`.
- Code changes in the host repo are mounted into `/workspace`; reloads happen automatically with `--reload`.

### Database access

- Connection string (also set as `DATABASE_URL`): `postgresql+psycopg://vd_bot:vd_bot@localhost:55432/vd_bot`.
- To open a psql shell:
  ```bash
  docker compose exec db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"
  ```
- Data is stored in the `pgdata` volume; remove the volume to reset state.

### Optional pgAdmin

The main compose file also ships with a pgAdmin service. After `docker compose up`, navigate to http://localhost:5050 and log in with `admin@example.com` / `admin` (override via `PGADMIN_DEFAULT_EMAIL` / `PGADMIN_DEFAULT_PASSWORD`).

- When registering the bundled Postgres server inside pgAdmin, use `db` as the host name, port `5432`, username/password `vd_bot` (or whatever you set in `.env`).
- To connect from pgAdmin to the database exposed to the host, use `localhost` and port `55432`.

## Local (non-Docker) commands

```bash
uv sync --python 3.11
uv run --python 3.11 -- python -c "import sys; print(sys.executable, sys.version)"
uv run --python 3.11 --env-file .env uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

## Knowledge base ingestion

- rag-ingest requires the project to be installed with uv sync

1. Place the files you want indexed under `app/rag_engine/storage/`. Subfolders are supported.
2. Ensure your `.env` (or environment) exposes the OpenAI credentials and any custom `RAG_*` overrides.
3. (Re)build the vector store:
   ```bash
   uv run --python 3.11 --env-file .env rag-ingest
   ```
   The command wipes the existing persisted vectors in `app/rag_engine/storage/vector_store/` and recreates them from the files in step 1.
   If the CLI entry point is unavailable, run:
   ```bash
   uv run --python 3.11 --env-file .env python -m app.rag_engine.ingest
   ```

## Twenty configuration

- Inside Twenty, create a `chatwoot_id` custom field on people so that the bot and CRM can keep records in sync.
