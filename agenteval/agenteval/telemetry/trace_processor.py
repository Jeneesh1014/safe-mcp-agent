"""
Trace processor — normalises flat span rows into typed evaluation records.

Design rule: spans are already flat in SQLite (the agent's exporter handles that).
This module structures them into domain-specific records for scoring.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel


class ToolCallRecord(BaseModel):
    tool_name: str
    args: dict[str, Any]
    blocked: bool = False
    block_reason: str | None = None
    block_technique: str | None = None
    result_redacted: bool = False
    result_redaction_technique: str | None = None
    error: str | None = None
    duration_ms: float = 0.0
    call_id: str = ""


class LLMCallRecord(BaseModel):
    model: str
    latency_ms: float
    tools_requested: list[str]
    message_count: int = 0


class RunSummary(BaseModel):
    total_duration_ms: float
    tool_call_count: int
    llm_call_count: int
    blocked_count: int
    error_count: int


def extract_tool_calls(spans: list[dict[str, Any]]) -> list[ToolCallRecord]:
    records = []
    for span in spans:
        if span.get("name") != "tool.dispatch":
            continue

        attrs = span.get("attributes", {})
        if isinstance(attrs, str):
            attrs = json.loads(attrs)

        args_raw = attrs.get("tool.args", "{}")
        try:
            args = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
        except (json.JSONDecodeError, TypeError):
            args = {"_raw": str(args_raw)}

        records.append(
            ToolCallRecord(
                tool_name=attrs.get("tool.name", "unknown"),
                args=args,
                blocked=attrs.get("tool.blocked") == "true",
                block_reason=attrs.get("tool.block_reason"),
                block_technique=attrs.get("tool.block_technique"),
                result_redacted=attrs.get("tool.result_redacted") == "true",
                result_redaction_technique=attrs.get("tool.result_redaction_technique"),
                error=attrs.get("tool.error"),
                duration_ms=span.get("duration_ms", 0.0),
                call_id=attrs.get("tool.call_id", ""),
            )
        )
    return records


def extract_llm_calls(spans: list[dict[str, Any]]) -> list[LLMCallRecord]:
    records = []
    for span in spans:
        if span.get("name") != "llm.reason":
            continue

        attrs = span.get("attributes", {})
        if isinstance(attrs, str):
            attrs = json.loads(attrs)

        tools_raw = attrs.get("gen_ai.response.tool_calls", "[]")
        try:
            tools = json.loads(tools_raw) if isinstance(tools_raw, str) else tools_raw
        except (json.JSONDecodeError, TypeError):
            tools = []

        latency_raw = attrs.get("llm.latency_ms", "0")
        try:
            latency = float(latency_raw)
        except (ValueError, TypeError):
            latency = 0.0

        msg_count_raw = attrs.get("message_count", "0")
        try:
            msg_count = int(msg_count_raw)
        except (ValueError, TypeError):
            msg_count = 0

        records.append(
            LLMCallRecord(
                model=attrs.get("gen_ai.request.model", "unknown"),
                latency_ms=latency,
                tools_requested=tools if isinstance(tools, list) else [],
                message_count=msg_count,
            )
        )
    return records


def extract_run_summary(spans: list[dict[str, Any]]) -> RunSummary:
    tool_calls = extract_tool_calls(spans)
    llm_calls = extract_llm_calls(spans)

    run_spans = [s for s in spans if s.get("name") == "agent.run"]
    if run_spans:
        total_duration = run_spans[0].get("duration_ms", 0.0)
    else:
        total_duration = sum(s.get("duration_ms", 0.0) for s in spans)

    return RunSummary(
        total_duration_ms=total_duration,
        tool_call_count=len(tool_calls),
        llm_call_count=len(llm_calls),
        blocked_count=sum(1 for tc in tool_calls if tc.blocked),
        error_count=sum(1 for tc in tool_calls if tc.error and not tc.blocked),
    )
