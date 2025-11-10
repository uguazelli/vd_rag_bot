# Chatwoot Service

Containerised Chatwoot instance used for the RevOps stack. This runs the Rails application and Postgres defined in `docker-compose.yaml`.

## Configuration

- Copy or edit the `.env` file in this directory before starting the stack.
- At minimum set `FRONTEND_URL` to the host Chatwoot will be served from (default is `http://0.0.0.0:3000` for local work).
- Populate any OAuth, SMTP, or storage credentials required by your deployment.

## Bootstrapping

```bash
# Run database migrations and seed data
docker compose run --rm rails bundle exec rails db:chatwoot_prepare

# Start the Chatwoot services in the background
docker compose up -d
```

Once the containers are healthy, open the frontend at the URL defined in `FRONTEND_URL`.

## Post-Setup Tasks

- When integrating with `vd_rag_bot`, expose the Chatwoot API (default `http://localhost:3000/api/v1`) and share the bot access token with the FastAPI service.

## Useful Commands

- `docker compose ps` – check service status.
- `docker compose logs -f rails` – tail the Rails application logs.
- `docker compose down` – stop and remove containers when you are finished.
