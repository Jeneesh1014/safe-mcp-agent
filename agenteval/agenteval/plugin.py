"""
pytest plugin — exposes the --agenteval flag and prints a summary report.

Registered via the [tool.poetry.plugins."pytest11"] entry point in
agenteval/pyproject.toml, so `pip install mcp-guardeval` makes
`pytest --agenteval` available in any project.

Configuration via pyproject.toml (all optional):

    [tool.pytest.ini_options]
    guardeval_techniques = ["SAFE-T1201", "MY-CUSTOM-001"]
    guardeval_log = "logs/guardrail.jsonl"
    guardeval_traces_db = "traces.db"
    guardeval_block_threshold = "0.0"

When guardeval_techniques is empty, technique IDs are auto-discovered
from the guardrail log file.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from agenteval.metrics.security import score_security_run
from agenteval.storage import TraceStore, discover_techniques


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--agenteval",
        action="store_true",
        default=False,
        help="Run AgentEval summary report after the test session.",
    )

    parser.addini(
        "guardeval_techniques",
        type="args",
        default=[],
        help=(
            "Technique IDs to evaluate (space-separated). "
            "Auto-discovered from log if omitted."
        ),
    )
    parser.addini(
        "guardeval_log",
        default="",
        help="Path to the guardrail JSONL log file.",
    )
    parser.addini(
        "guardeval_traces_db",
        default="",
        help="Path to the OpenTelemetry traces SQLite database.",
    )
    parser.addini(
        "guardeval_block_threshold",
        default="0.0",
        help="Minimum block rate (0.0–1.0) for the session to be considered secure.",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "security: marks security attack tests")


def _resolve_path(ini_value: str, env_var: str, fallback: str) -> Path:
    """Resolve a path from ini config → env var → hardcoded fallback."""
    if ini_value:
        return Path(ini_value)
    env = os.environ.get(env_var, "")
    if env:
        return Path(env)
    return Path(fallback)


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    if not session.config.getoption("--agenteval", default=False):
        return

    cfg = session.config

    traces_db = _resolve_path(
        cfg.getini("guardeval_traces_db"),
        "TRACES_DB",
        "traces.db",
    )
    guardrail_log = _resolve_path(
        cfg.getini("guardeval_log"),
        "GUARDRAIL_LOG",
        "guardrail.log",
    )

    writer = cfg.pluginmanager.get_plugin("terminalreporter")
    if not writer:
        return

    writer.write_sep("=", "AgentEval Summary")

    if not traces_db.exists():
        writer.write_line(f"  traces.db not found at {traces_db}")
        return

    store = TraceStore(traces_db)
    all_traces = store.get_all_traces()
    writer.write_line(f"  Traces in DB: {len(all_traces)}")

    all_spans = []
    for trace_id in all_traces:
        all_spans.extend(store.get_spans_by_trace(trace_id))

    dispatch_spans = [s for s in all_spans if s.get("name") == "tool.dispatch"]
    blocked_spans = [
        s
        for s in dispatch_spans
        if s.get("attributes", {}).get("tool.blocked") == "true"
    ]
    writer.write_line(f"  Tool dispatches: {len(dispatch_spans)}")
    writer.write_line(f"  Blocked by guardrail: {len(blocked_spans)}")

    if not guardrail_log.exists():
        writer.write_line(f"  Guardrail log not found at {guardrail_log}")
        return

    # Technique list: explicit config → auto-discover from log
    techniques = list(cfg.getini("guardeval_techniques"))
    if not techniques:
        techniques = discover_techniques(guardrail_log)
        if techniques:
            writer.write_line(
                f"  Auto-discovered {len(techniques)} techniques from log"
            )

    if not techniques:
        writer.write_line(
            "  No techniques configured or discovered — skipping security scoring"
        )
        writer.write_sep("=", "")
        return

    result = score_security_run(
        spans=all_spans,
        guardrail_log_path=str(guardrail_log),
        expected_techniques=techniques,
    )

    writer.write_line(
        f"  Block rate: {result.block_rate:.0%} "
        f"({result.blocked_count}/{result.total_attacks})"
    )
    writer.write_line("")
    for v in result.verdicts:
        marker = (
            "✓" if v.verdict == "BLOCKED" else "✗" if v.verdict == "PASSED" else "~"
        )
        writer.write_line(f"    {marker} {v.technique_id}: {v.verdict}")

    # Threshold check
    try:
        threshold = float(cfg.getini("guardeval_block_threshold"))
    except (ValueError, TypeError):
        threshold = 0.0

    if threshold > 0.0:
        writer.write_line("")
        if result.block_rate >= threshold:
            writer.write_line(
                f"  ✓ Block rate {result.block_rate:.0%} "
                f"meets threshold {threshold:.0%}"
            )
        else:
            writer.write_line(
                f"  ✗ Block rate {result.block_rate:.0%} "
                f"below threshold {threshold:.0%}"
            )

    writer.write_sep("=", "")
