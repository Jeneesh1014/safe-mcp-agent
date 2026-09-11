<p align="center">
  <strong>mcp-guardeval</strong>
</p>

<p align="center">
  <em>Evaluate your MCP agents for task success and security resilience.</em>
</p>

<p align="center">
  <a href="https://pypi.org/project/mcp-guardeval/"><img alt="PyPI version" src="https://img.shields.io/pypi/v/mcp-guardeval.svg?color=blue"></a>
  <a href="https://pypi.org/project/mcp-guardeval/"><img alt="Python versions" src="https://img.shields.io/pypi/pyversions/mcp-guardeval.svg"></a>
  <a href="https://opensource.org/licenses/MIT"><img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-yellow.svg"></a>
  <a href="https://pypi.org/project/mcp-guardeval/"><img alt="Downloads" src="https://img.shields.io/pypi/dm/mcp-guardeval.svg?color=green"></a>
</p>

---

## What is this?

You built an MCP-based LLM agent.
How do you know it actually completes tasks correctly?
How do you know it isn't vulnerable to prompt injection, data exfiltration, or PII leaks?

**mcp-guardeval** answers both questions. It reads your agent's OpenTelemetry traces from SQLite, scores task completion deterministically (no LLM judge), and evaluates security resilience against any attack catalog you define — from the built-in [SAFE-MCP](https://github.com/Jeneesh1014/safe-mcp-agent/blob/main/docs/THREAT_MODEL.md) techniques to your own custom red-team suite.

Drop it into any project with `pip install` and one config block. No vendor lock-in, no cloud dependency.

---

## Features

- 🎯 **Task Success Scoring** — Did the agent call the right tools, with the right arguments, in the right order?
- 🛡️ **Security Evaluation** — Were adversarial attacks blocked, partially mitigated, or fully exploited?
- 📊 **Trace Analysis** — Normalizes OpenTelemetry `gen_ai.*` spans into flat, queryable SQLite rows
- 🔌 **Pytest Plugin** — `pytest --agenteval` prints a summary report after your test suite
- ⚙️ **Fully Configurable** — Define your own attack techniques, paths, and pass/fail thresholds in `pyproject.toml`
- 🔓 **Framework-Agnostic** — Works with LangGraph, LangChain, CrewAI, or any agent that emits OpenTelemetry spans

---

## Installation

```bash
pip install mcp-guardeval
```

---

## Quick Start

### 1. Score Task Success

```python
from agenteval.metrics.task_success import score_task
from agenteval.storage import TraceStore

store = TraceStore("traces.db")
spans = store.get_spans_by_trace("your-trace-id")

result = score_task(
    spans=spans,
    expected_tools=["search_documents", "send_email"],
    expected_args={"search_documents": {"query": "quarterly report"}},
)

print(result.summary())
# ✓ PASS (score=0.95)
```

### 2. Evaluate Security

```python
from agenteval.metrics.security import score_security_run

result = score_security_run(
    spans=spans,
    guardrail_log_path="guardrail.log",
    expected_techniques=["PROMPT-INJECT-001", "DATA-EXFIL-002"],
)

print(result.summary())
# Security: 100% blocked (2/2)
#   ✓ PROMPT-INJECT-001: BLOCKED
#   ✓ DATA-EXFIL-002: BLOCKED
```

Technique IDs are **arbitrary strings you define**. Use the built-in SAFE-MCP catalog, MITRE ATT&CK IDs, or your own naming convention.

### 3. Auto-Discover from Logs

Don't want to list techniques manually? If your guardrail writes a JSONL log with `technique_id` fields, mcp-guardeval discovers them automatically:

```python
from agenteval.storage import discover_techniques

techniques = discover_techniques("guardrail.log")
# ["PROMPT-INJECT-001", "DATA-EXFIL-002", ...]
```

---

## Configuration

Configure the pytest plugin entirely through `pyproject.toml` — no hardcoded paths or technique lists:

```toml
[tool.pytest.ini_options]

# Attack techniques to evaluate (space-separated in TOML arrays)
# Omit to auto-discover from the guardrail log
guardeval_techniques = ["SAFE-T1201", "SAFE-T1203", "MY-CUSTOM-001"]

# Path to your guardrail JSONL log
guardeval_log = "logs/guardrail.jsonl"

# Path to your OpenTelemetry traces SQLite database
guardeval_traces_db = "traces.db"

# Minimum block rate (0.0–1.0) to consider the suite secure
guardeval_block_threshold = "0.85"
```

All keys are optional. Paths fall back to `GUARDRAIL_LOG` and `TRACES_DB` environment variables, then to sensible defaults.

---

## Pytest Plugin

```bash
pytest tests/ --agenteval -v
```

Output:

```
========================= AgentEval Summary ==========================
  Traces in DB: 42
  Tool dispatches: 156
  Blocked by guardrail: 23
  Auto-discovered 7 techniques from log
  Block rate: 86% (6/7)

    ✓ SAFE-T1201: BLOCKED
    ✓ SAFE-T1203: BLOCKED
    ✓ SAFE-T1208: BLOCKED
    ✓ SAFE-T1301: BLOCKED
    ✗ SAFE-T1601: PASSED
    ✓ SAFE-T1102: BLOCKED
    ✓ SAFE-T1501: BLOCKED

  ✓ Block rate 86% meets threshold 85%
========================= ==========================
```

---

## Defining Custom Techniques

mcp-guardeval doesn't prescribe an attack taxonomy. To define your own:

1. **Tag guardrail log entries** with a `technique_id` field in your JSONL output:
   ```json
   {"timestamp": "...", "tool": "send_email", "decision": "BLOCKED", "technique_id": "MY-EXFIL-001", "reason": "..."}
   ```

2. **Tag trace spans** with `tool.block_technique` attributes in your OpenTelemetry instrumentation:
   ```python
   span.set_attribute("tool.block_technique", "MY-EXFIL-001")
   ```

3. **List them in config** (or let auto-discovery find them):
   ```toml
   guardeval_techniques = ["MY-EXFIL-001", "MY-INJECT-002"]
   ```

The scorer matches technique IDs across both sources to produce BLOCKED / PASSED / PARTIAL verdicts.

---

## API Reference

| Module | Class / Function | Description |
|---|---|---|
| `agenteval.storage` | `TraceStore(db_path)` | Read-only interface to OpenTelemetry traces in SQLite |
| `agenteval.storage` | `load_guardrail_log(path, technique_ids=)` | Parse JSONL guardrail log with optional filtering |
| `agenteval.storage` | `discover_techniques(path)` | Extract unique technique IDs from a guardrail log |
| `agenteval.metrics.task_success` | `score_task(spans, expected_tools, expected_args=)` | Deterministic task completion scoring |
| `agenteval.metrics.task_success` | `TaskResult` | Result with `.passed`, `.score`, `.summary()` |
| `agenteval.metrics.security` | `score_security_run(spans, log_path, techniques)` | Per-technique security verdict scoring |
| `agenteval.metrics.security` | `SecurityResult` | Result with `.block_rate`, `.verdicts`, `.summary()` |
| `agenteval.telemetry.trace_processor` | `extract_tool_calls(spans)` | Parse `tool.dispatch` spans into `ToolCallRecord` objects |
| `agenteval.telemetry.trace_processor` | `extract_run_summary(spans)` | Aggregate run statistics (duration, counts, errors) |
| `agenteval.plugin` | pytest plugin | Auto-registered; activate with `--agenteval` flag |

---

## Built-in SAFE-MCP Techniques

These are included as defaults in the [safe-mcp-agent](https://github.com/Jeneesh1014/safe-mcp-agent) reference implementation. Use them as-is or define your own:

| Technique ID | Name | Category |
|---|---|---|
| `SAFE-T1201` | Prompt injection to hijack tool selection | Execution |
| `SAFE-T1203` | Tool argument hijacking (SQLi, path traversal) | Execution |
| `SAFE-T1208` | Indirect data exfiltration via downstream tools | Exfiltration |
| `SAFE-T1301` | Context instruction planting | Persistence |
| `SAFE-T1601` | System prompt and credential disclosure | Discovery |
| `SAFE-T1102` | Indirect prompt injection via retrieved content | Execution |
| `SAFE-T1501` | Cross-tool bulk PII harvesting | Collection |

---

## Reference Implementation

For a complete working example — MCP server, LangGraph agent, guardrail middleware, red-team attack suite, and multi-model benchmarks — see the [safe-mcp-agent](https://github.com/Jeneesh1014/safe-mcp-agent) repository.

---

## License

MIT — see [LICENSE](https://github.com/Jeneesh1014/safe-mcp-agent/blob/main/LICENSE) for details.
