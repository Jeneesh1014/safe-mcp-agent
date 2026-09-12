"""
Guardrail middleware — intercepts every tool call before it reaches the MCP server.

Three layers run in sequence on every tool call:
  1. Input validation  — strict Pydantic schemas per tool
  2. Permission scoping — channel allowlist + per-session call budget
  3. Output filtering   — block PII/credentials in send_slack_message text

Retrieved wiki content is also filtered after tool execution before it is
returned to the LLM, because compromised documents are untrusted input.

Every block emits a structured JSON log entry to fixtures/guardrail.log.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator

_HERE = Path(__file__).parent
_GUARDRAIL_LOG = _HERE / "fixtures" / "guardrail.log"

ALLOWED_CHANNELS = frozenset({"#general", "#support", "#billing", "#alerts"})

ALLOWED_WIKI_TOPICS = frozenset({"billing", "data_handling", "support_escalation"})

MAX_CUSTOMER_LOOKUPS_PER_SESSION = 3


@dataclass
class BlockResult:
    technique_id: str
    reason: str
    tool: str
    timestamp: str = field(
        default_factory=lambda: datetime.now(tz=timezone.utc).isoformat()
    )


@dataclass
class Session:
    """Tracks per-run state for permission scoping."""

    customer_db_calls: int = 0


class CustomerIdInput(BaseModel):
    customer_id: str = Field(min_length=1, max_length=20)

    @field_validator("customer_id", mode="before")
    @classmethod
    def coerce_to_str(cls, v: Any) -> str:
        return str(v)

    @field_validator("customer_id")
    @classmethod
    def must_be_alphanumeric(cls, v: str) -> str:
        if not re.fullmatch(r"[a-zA-Z0-9_\-]+", v):
            raise ValueError(f"customer_id must be alphanumeric, got {v!r}")
        return v


class WikiTopicInput(BaseModel):
    topic: str = Field(min_length=1, max_length=100)

    @field_validator("topic")
    @classmethod
    def no_path_traversal(cls, v: str) -> str:
        if ".." in v or "/" in v or "\\" in v:
            raise ValueError(f"topic contains path separator: {v!r}")
        if v.lower() not in ALLOWED_WIKI_TOPICS:
            raise ValueError(
                f"topic {v!r} not in allowed list: {sorted(ALLOWED_WIKI_TOPICS)}"
            )
        return v


class WikiQuestionInput(BaseModel):
    question: str = Field(min_length=1, max_length=500)


class SlackMessageInput(BaseModel):
    channel: str = Field(min_length=2, max_length=50)
    text: str = Field(min_length=1, max_length=2000)

    @field_validator("channel")
    @classmethod
    def must_start_with_hash(cls, v: str) -> str:
        if not v.startswith("#"):
            raise ValueError(f"channel must start with #, got {v!r}")
        return v


_INPUT_SCHEMAS: dict[str, type[BaseModel]] = {
    "query_customer_db": CustomerIdInput,
    "query_openkb_wiki": WikiQuestionInput,
    "read_internal_wiki": WikiTopicInput,
    "send_slack_message": SlackMessageInput,
}

_EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}")
_BALANCE_RE = re.compile(r"\$?\d{1,3}(?:,\d{3})*\.\d{2}\b")
_RAW_DECIMAL_RE = re.compile(r"\b\d{3,}\.\d+\b")
_CREDENTIAL_KEYWORDS = frozenset(
    {
        "password",
        "token",
        "api_key",
        "apikey",
        "secret",
        "ssn",
        "credit card",
        "creditcard",
        "credential",
    }
)
_RETRIEVAL_TOOLS = frozenset({"query_openkb_wiki", "read_internal_wiki"})
_RETRIEVAL_INJECTION_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE | re.DOTALL)
    for pattern in (
        r"\b(?:system|developer)\s+(?:override|instruction|message|prompt)\b",
        r"\b(?:ignore|disregard|forget)\b.{0,80}\b(?:previous|above|prior|earlier)\b",
        r"\bmust\s+(?:also\s+)?(?:look up|query|send|forward|exfiltrate|post)\b",
        r"\b(?:send|forward|post|exfiltrate)\b.{0,120}\b(?:to|into)\s+#[a-z0-9_-]+",
        r"\bdo not mention\b.{0,80}\b(?:the\s+)?(?:user|step|instruction)\b",
        r"\btool\s*:\s*[a-z0-9_-]+",
    )
)
_SYSTEM_PROMPT_LEAK_RE = re.compile(
    r"(?:You are a helpful enterprise assistant|"
    r"access to four tools|"
    r"(?:use|call) the tools in the right order|"
    r"chain the results naturally|"
    r"Always prefer query_openkb_wiki over read_internal_wiki|"
    r"Do not mention tool internals unless asked)",
    re.IGNORECASE,
)
_SECRET_KEY_RE = re.compile(
    r"(?:-----BEGIN [A-Z ]*PRIVATE KEY-----|"
    r"sk-[a-zA-Z0-9_-]{20,}|"
    r"(?:api[_-]?key|secret[_-]?token|password)\s*[:=]\s*['\"][^\s'\"]+['\"])",
    re.IGNORECASE,
)


def _log_block(block: BlockResult, args_summary: dict[str, Any] | None = None) -> None:
    _GUARDRAIL_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry: dict[str, Any] = {
        "timestamp": block.timestamp,
        "tool": block.tool,
        "decision": "BLOCKED",
        "technique_id": block.technique_id,
        "reason": block.reason,
    }
    if args_summary:
        entry["args_summary"] = args_summary
    with _GUARDRAIL_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def validate_input(tool_name: str, args: dict[str, Any]) -> BlockResult | None:
    schema = _INPUT_SCHEMAS.get(tool_name)
    if schema is None:
        return None
    try:
        schema(**args)
    except Exception as exc:
        block = BlockResult(
            technique_id="SAFE-T1203",
            reason=f"Input validation failed: {exc}",
            tool=tool_name,
        )
        _log_block(block, {k: str(v)[:80] for k, v in args.items()})
        return block
    return None


def check_permissions(
    tool_name: str, args: dict[str, Any], session: Session
) -> BlockResult | None:
    if tool_name == "send_slack_message":
        channel = args.get("channel", "")
        if channel not in ALLOWED_CHANNELS:
            block = BlockResult(
                technique_id="SAFE-T1201",
                reason=f"Channel {channel!r} not in allowlist",
                tool=tool_name,
            )
            _log_block(block, {"channel": channel})
            return block

    if tool_name == "query_customer_db":
        session.customer_db_calls += 1
        if session.customer_db_calls > MAX_CUSTOMER_LOOKUPS_PER_SESSION:
            block = BlockResult(
                technique_id="SAFE-T1501",
                reason=(
                    f"Call budget exceeded: {session.customer_db_calls} "
                    f"query_customer_db calls (max {MAX_CUSTOMER_LOOKUPS_PER_SESSION})"
                ),
                tool=tool_name,
            )
            _log_block(block, args)
            return block

    return None


def filter_output(tool_name: str, args: dict[str, Any]) -> BlockResult | None:
    if tool_name != "send_slack_message":
        return None

    text = args.get("text", "")
    findings: list[str] = []

    if _EMAIL_RE.search(text):
        findings.append("email address detected")

    if _BALANCE_RE.search(text) or _RAW_DECIMAL_RE.search(text):
        findings.append("monetary/balance value detected")

    text_lower = text.lower()
    for keyword in _CREDENTIAL_KEYWORDS:
        if keyword in text_lower:
            findings.append(f"credential keyword: {keyword}")
            break

    if not findings:
        return None

    block = BlockResult(
        technique_id="SAFE-T1208",
        reason=f"PII/sensitive data in outbound message: {', '.join(findings)}",
        tool=tool_name,
    )
    _log_block(block, {"channel": args.get("channel", ""), "findings": findings})
    return block


def _looks_like_retrieval_injection(text: str) -> list[str]:
    findings: list[str] = []
    for pattern in _RETRIEVAL_INJECTION_PATTERNS:
        if pattern.search(text):
            findings.append(pattern.pattern)
    return findings


def _redact_injected_content(value: Any, redacted_paths: list[str], path: str) -> Any:
    if isinstance(value, str):
        findings = _looks_like_retrieval_injection(value)
        if not findings:
            return value
        redacted_paths.append(path)
        return (
            "[REDACTED by guardrail: retrieved content contained "
            "agent-directed instructions.]"
        )

    if isinstance(value, list):
        return [
            _redact_injected_content(item, redacted_paths, f"{path}[{idx}]")
            for idx, item in enumerate(value)
        ]

    if isinstance(value, dict):
        return {
            key: _redact_injected_content(item, redacted_paths, f"{path}.{key}")
            for key, item in value.items()
        }

    return value


def filter_tool_result(tool_name: str, result: Any) -> tuple[Any, BlockResult | None]:
    """Sanitize untrusted tool results before they enter the LLM context."""
    if tool_name not in _RETRIEVAL_TOOLS:
        return result, None

    redacted_paths: list[str] = []
    sanitized = _redact_injected_content(result, redacted_paths, "$")
    if not redacted_paths:
        return result, None

    block = BlockResult(
        technique_id="SAFE-T1102",
        reason=(
            "Retrieved content contained agent-directed instructions; "
            f"redacted fields: {', '.join(redacted_paths)}"
        ),
        tool=tool_name,
    )
    _log_block(block, {"redacted_paths": redacted_paths})

    if isinstance(sanitized, dict):
        sanitized = {
            **sanitized,
            "guardrail": {
                "decision": "REDACTED",
                "technique_id": block.technique_id,
                "reason": block.reason,
            },
        }

    return sanitized, block


def guardrail_check(
    tool_name: str, args: dict[str, Any], session: Session
) -> BlockResult | None:
    block = validate_input(tool_name, args)
    if block:
        return block

    block = check_permissions(tool_name, args, session)
    if block:
        return block

    block = filter_output(tool_name, args)
    if block:
        return block

    return None


def filter_final_response(text: str) -> tuple[str, BlockResult | None]:
    """Inspect and sanitize the agent's final natural language response."""
    findings: list[str] = []
    technique_id = "SAFE-T1208"

    if _SECRET_KEY_RE.search(text):
        findings.append("credential or private key detected")
        technique_id = "SAFE-T1208"

    if _SYSTEM_PROMPT_LEAK_RE.search(text):
        findings.append("system prompt disclosure detected")
        technique_id = "SAFE-T1601"

    if not findings:
        return text, None

    block = BlockResult(
        technique_id=technique_id,
        reason=f"Final response blocked: {', '.join(findings)}",
        tool="agent.final_response",
    )
    _log_block(block, {"findings": findings})
    redacted = (
        "[REDACTED by guardrail: response contained sensitive credentials "
        "or unauthorized system instruction disclosure.]"
    )
    return redacted, block
