# syntax=docker/dockerfile:1

FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:/root/.local/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv (Python packaging tool)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

WORKDIR /workspace

COPY requirements.txt .

# Create the virtual environment and install project dependencies using uv
RUN uv venv "$UV_PROJECT_ENVIRONMENT" && \
    uv pip install --python "$UV_PROJECT_ENVIRONMENT/bin/python" -r requirements.txt

COPY . .

EXPOSE 8080

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--reload"]
