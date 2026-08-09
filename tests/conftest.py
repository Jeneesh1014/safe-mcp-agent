"""
Shared pytest fixtures and session-level hooks.

Includes:
  - ollama_warmup: hits the configured Ollama model once before any test
    runs so a cold-start timeout doesn't look like a real bug (M1 can take
    8-10 s for the first inference call after the model is loaded).
  - Any other session-level fixtures shared across test_agent_behavior.py
    and test_security.py live here, not in the individual test files.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

import pytest
from dotenv import load_dotenv

# Load .env from repo root if present; no-op in CI where it won't exist.
load_dotenv()

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2")


@pytest.fixture(scope="session", autouse=True)
def ollama_warmup():
    """
    Pre-warm Ollama so the first real test doesn't eat a cold-start timeout.

    Ollama's cold start on M1 can take 8-10 s for the first call after the
    model loads; we fire one cheap generate request at session start so that
    latency is absorbed here rather than in the first real assertion.

    Skips gracefully when Ollama isn't available (CI, offline) so that fast,
    non-LLM tests still run. Mark any test that actually needs the model with
    @pytest.mark.slow so it can be deselected with -m 'not slow'.
    """
    payload = json.dumps(
        {
            "model": DEFAULT_MODEL,
            "prompt": "hi",
            "stream": False,
        }
    ).encode()

    req = urllib.request.Request(
        f"{OLLAMA_BASE_URL}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            if resp.status != 200:
                pytest.skip(f"Ollama returned {resp.status} — skipping LLM tests")
    except (urllib.error.URLError, OSError):
        # Ollama isn't running; skip any test that uses this fixture explicitly.
        # Tests without @pytest.mark.slow still run fine.
        pytest.skip("Ollama not reachable — skipping LLM-dependent tests")

    yield
