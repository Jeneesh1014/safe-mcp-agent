"""
Shared pytest fixtures and session-level hooks.

Includes:
  - ollama_warmup: hits the configured Ollama model once before any test
    runs so a cold-start timeout doesn't look like a real bug (M1 can take
    8-10 s for the first inference call after the model is loaded).
  - Any other session-level fixtures shared across test_agent_behavior.py
    and test_security.py live here, not in the individual test files.
"""

import pytest

OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "llama3.2"  # override via OLLAMA_MODEL env var if needed


@pytest.fixture(scope="session", autouse=True)
def ollama_warmup():
    """
    Pre-warm Ollama so the first real test doesn't eat a cold-start timeout.

    Ollama's cold start on M1 can take 8-10 s for the first call; we send
    one cheap inference request at session start so the model is loaded by
    the time the actual tests run.
    """
    # TODO(week-1): implement pre-warm — hit OLLAMA_BASE_URL/api/generate
    # with a minimal prompt and assert status 200 before yielding.
    yield
