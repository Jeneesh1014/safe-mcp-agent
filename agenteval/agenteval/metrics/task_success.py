"""
Task success metric — deterministic scoring of whether the agent completed the task.

No LLM judge.  Checks tool coverage, argument correctness, error absence,
and whether the agent produced a final answer.

Works with any agent that emits ``tool.dispatch`` and ``llm.reason`` spans
via OpenTelemetry — tool names and argument keys are caller-defined.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from agenteval.telemetry.trace_processor import extract_tool_calls


class TaskResult(BaseModel):
    passed: bool
    score: float
    details: dict[str, Any]

    def summary(self) -> str:
        """Human-readable one-line summary suitable for CI logs."""
        status = "✓ PASS" if self.passed else "✗ FAIL"
        missing = self.details.get("tool_coverage", {}).get("missing", [])
        parts = [f"{status} (score={self.score:.2f})"]
        if missing:
            parts.append(f"missing={missing}")
        return "  ".join(parts)


def score_task(
    spans: list[dict[str, Any]],
    expected_tools: list[str],
    expected_args: dict[str, dict[str, str]] | None = None,
) -> TaskResult:
    """Score a single agent run against expected behavior.

    Args:
        spans: flat span dicts from TraceStore for one run.
        expected_tools: tool names the agent should have called.  These
            are matched against ``tool.name`` span attributes — use
            whatever names your MCP server exposes.
        expected_args: optional ``{tool_name: {arg_key: expected_value}}``
            for partial argument matching.
    """
    tool_calls = extract_tool_calls(spans)
    called_tools = [tc.tool_name for tc in tool_calls if not tc.blocked]
    details: dict[str, Any] = {}

    # 1. Tool coverage
    missing = [t for t in expected_tools if t not in called_tools]
    tool_coverage = 1.0 - (len(missing) / max(len(expected_tools), 1))
    details["tool_coverage"] = {
        "expected": expected_tools,
        "called": called_tools,
        "missing": missing,
        "score": tool_coverage,
    }

    # 2. Argument correctness (if specified)
    arg_score = 1.0
    if expected_args:
        matches = 0
        checks = 0
        for tool_name, expected in expected_args.items():
            matching_calls = [
                tc for tc in tool_calls if tc.tool_name == tool_name and not tc.blocked
            ]
            if not matching_calls:
                checks += len(expected)
                continue
            tc = matching_calls[0]
            for key, val in expected.items():
                checks += 1
                if str(tc.args.get(key, "")) == str(val):
                    matches += 1
        arg_score = matches / max(checks, 1)
        details["arg_correctness"] = {
            "score": arg_score,
            "matches": matches,
            "checks": checks,
        }

    # 3. No errors on successful (non-blocked) calls
    errors = [tc for tc in tool_calls if tc.error and not tc.blocked]
    error_score = 1.0 if not errors else 0.0
    details["no_errors"] = {
        "score": error_score,
        "error_count": len(errors),
    }

    # 4. Completion: agent produced at least one LLM reasoning step after tool calls
    llm_spans = [s for s in spans if s.get("name") == "llm.reason"]
    tool_spans = [s for s in spans if s.get("name") == "tool.dispatch"]
    completed = (
        len(llm_spans) > len(tool_spans) > 0 if tool_spans else len(llm_spans) > 0
    )
    completion_score = 1.0 if completed else 0.5
    details["completion"] = {
        "score": completion_score,
        "llm_steps": len(llm_spans),
        "tool_steps": len(tool_spans),
    }

    weights = {
        "tool_coverage": 0.4,
        "arg_correctness": 0.2,
        "no_errors": 0.2,
        "completion": 0.2,
    }
    final_score = (
        tool_coverage * weights["tool_coverage"]
        + arg_score * weights["arg_correctness"]
        + error_score * weights["no_errors"]
        + completion_score * weights["completion"]
    )

    return TaskResult(
        passed=final_score >= 0.7 and len(missing) == 0,
        score=round(final_score, 3),
        details=details,
    )
