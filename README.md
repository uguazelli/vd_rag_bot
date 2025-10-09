# Chatwoot + HubSpot Numeric Menu Bot (Starter Kit) — v2

## Running with Docker

1. Copy the sample environment and tweak as needed:
 ```bash
  cp .env.example .env
  ```
2. Build and start the stack (FastAPI app + PostgreSQL):
  ```bash
  docker compose up --build
  ```
  The API is exposed on http://localhost:8080.

### Coding inside the container

- Open a shell with all dependencies installed:
  ```bash
  docker compose exec app bash
  ```
- The image ships with the `uv` Python tool; run project commands such as `uv run uvicorn app.main:app --reload` or `uv pip list`.
- Host code changes are mounted into `/workspace`, so edits on your machine are reflected immediately.

### Database access

- Connection string (also set as `DATABASE_URL`): `postgresql+psycopg://vd_bot:vd_bot@localhost:5432/vd_bot`
- PgAdmin / CLI connections use user `vd_bot`, password `vd_bot`, database `vd_bot`.
- To open a psql shell:
  ```bash
  docker compose exec db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"
  ```

## Local (non-Docker) commands

```bash
uv run --python 3.11 -- python -c "import sys; print(sys.executable, sys.version)"
uv run --python 3.11 --env-file .env uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```
