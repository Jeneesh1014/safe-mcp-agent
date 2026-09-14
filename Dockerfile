FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Install poetry
RUN pip install --no-cache-dir poetry==1.8.3

WORKDIR /app

# Disable virtualenv creation inside container
RUN poetry config virtualenvs.create false

# Copy dependency specifications first for layer caching
COPY pyproject.toml poetry.lock ./
COPY agenteval/pyproject.toml ./agenteval/pyproject.toml
COPY agenteval/README.md ./agenteval/README.md
COPY agenteval/agenteval ./agenteval/agenteval

# Install dependencies and editable agenteval library
RUN poetry install --no-interaction --no-ansi --no-root && \
    pip install -e ./agenteval

# Copy application codebase and fixtures
COPY reference_system ./reference_system
COPY attacks ./attacks
COPY tests ./tests
COPY scripts ./scripts
COPY docs ./docs
COPY wiki ./wiki
COPY .env.example ./.env

# Default environment configuration
RUN mkdir -p /app/traces /app/benchmark_output

ENV PYTHONUNBUFFERED=1 \
    OLLAMA_BASE_URL=http://host.docker.internal:11434 \
    OLLAMA_MODEL=llama3.2 \
    TRACES_DB=/app/traces/traces.db

# Default execution: run the security evaluation suite
CMD ["poetry", "run", "pytest", "tests/test_security.py", "-v"]
