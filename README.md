# VD-REVOPS

Collection of RevOps tooling that runs Chatwoot, Twenty CRM, and a retrieval-augmented bot side by side. Each project lives in its own directory and can be started independently, but they are designed to work together for customer engagement and data sync flows.

## Prerequisites

- Docker Engine 24+ and Docker Compose plugin
- `git` for managing this repository
- Access tokens and secrets for Chatwoot, Twenty, and OpenAI before going to production (sample `.env` files are provided)

## Directory Layout

- `chatwoot/` – Dockerised Chatwoot instance ready for local testing; see `chatwoot/README.md`
- `twenty/` – Docker compose setup for Twenty CRM; see `twenty/README.md`
- `vd_rag_bot/` – FastAPI bot that bridges Chatwoot with AI responses; see `vd_rag_bot/README.md`

## Getting Started

1. Clone the repository and pull submodules if any: `git clone <repo-url>`
2. Pick the component you want to work on and follow its README to configure environment variables.
3. Start the relevant stack with Docker Compose: each directory contains its own `docker-compose.yml`.
4. Once services are running you can wire them together (e.g., point the bot to Chatwoot and Twenty URLs) using the variables documented per project.

## Next Steps

- Review each subproject README for component-specific environment variables, data seeding, and troubleshooting tips.
- Commit any environment or configuration changes to your own copies of the `.env` files—production secrets should never be committed.
- If you update container images or dependencies, keep the READMEs in sync so the team understands new requirements.
