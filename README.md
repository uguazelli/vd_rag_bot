# Chatwoot + HubSpot Numeric Menu Bot (Starter Kit) — v2

uv run --python 3.11 -- python -c "import sys; print(sys.executable, sys.version)"

uv run --python 3.11 --env-file .env uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
