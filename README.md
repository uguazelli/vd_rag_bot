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
   - `TWENTY_BASE_URL` and `TWENTY_API_KEY` if you want contact syncing with Twenty.
   - Database credentials if you override the defaults supplied in `docker-compose.yml`.

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

## Local (non-Docker) commands

```bash
uv run --python 3.11 -- python -c "import sys; print(sys.executable, sys.version)"
uv run --python 3.11 --env-file .env uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```
