"""
agenteval — automated evaluation library for MCP-based LLM agents.

Published to PyPI as ``mcp-guardeval`` (pip install mcp-guardeval).
Importable as ``import agenteval``.

Deterministic scoring of task success and security resilience using
OpenTelemetry traces — no LLM judge, no cloud dependency.

Quick start::

    from agenteval import TraceStore, score_task, score_security_run

    store = TraceStore("traces.db")
    spans = store.get_spans_by_trace("your-trace-id")

    task = score_task(spans, expected_tools=["search_documents", "send_email"])
    print(task.summary())

This package must stay independently installable. It must not import
anything from reference_system/ at module load time.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("mcp-guardeval")
except PackageNotFoundError:
    # Running from source without pip install
    __version__ = "0.3.0.dev0"

# Public API — flat re-exports so callers don't need deep imports.
from agenteval.metrics.security import (
    SecurityResult,
    TechniqueVerdict,
    score_security_run,
)
from agenteval.metrics.task_success import TaskResult, score_task
from agenteval.storage import TraceStore, discover_techniques, load_guardrail_log
from agenteval.telemetry.trace_processor import (
    LLMCallRecord,
    RunSummary,
    ToolCallRecord,
    extract_llm_calls,
    extract_run_summary,
    extract_tool_calls,
)

__all__ = [
    "__version__",
    # Storage
    "TraceStore",
    "load_guardrail_log",
    "discover_techniques",
    # Scoring
    "score_task",
    "TaskResult",
    "score_security_run",
    "SecurityResult",
    "TechniqueVerdict",
    # Telemetry
    "ToolCallRecord",
    "LLMCallRecord",
    "RunSummary",
    "extract_tool_calls",
    "extract_llm_calls",
    "extract_run_summary",
]
