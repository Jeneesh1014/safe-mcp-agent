# Threat Model

This document is a living record. Update it when tools change, when a new
attack vector is discovered, or when a mitigation changes. It must reflect
the actual system, not the plan — go back and correct anything that drifts.

## Scope

The threat surface is the boundary between the LangGraph agent and the MCP
server. Anything inside that boundary (the agent's reasoning, the LLM's
outputs) is in scope. The LLM itself is treated as partially adversarial —
it can be manipulated by injected text in its context window.

## Assets

| Asset | Sensitivity | Location |
|---|---|---|
| Customer records (name, email, balance) | High — PII + financial | `reference_system/fixtures/customers.db` |
| Internal wiki content | Medium — internal policy | `reference_system/fixtures/wiki/` |
| Message log | High — outbound channel | `reference_system/fixtures/messages.log` |

## Threat actors

- **Prompt injector** — embeds adversarial instructions in user-supplied input
  or in data retrieved from a tool (e.g. a wiki page with hidden instructions).
- **Argument manipulator** — sends malformed tool arguments hoping to bypass
  validation or trigger unexpected behaviour.
- **Data exfiltrator** — chains legitimate tool calls to move sensitive data
  into an outbound tool (`send_slack_message`).

## Technique coverage

| Technique ID | Name | Category | Status | Mitigation in `middleware.py` |
|---|---|---|---|---|
| SAFE-T1201 | Prompt injection — tool hijack | Execution | 🟢 Blocked | Channel allowlist in `check_permissions` |
| SAFE-T1203 | Tool argument hijacking | Execution | 🟢 Blocked | Pydantic v2 schemas in `validate_input` |
| SAFE-T1208 | Indirect data exfiltration | Exfiltration | 🟢 Blocked | Channel allowlist + PII regex in `filter_output` |
| SAFE-T1301 | Context instruction planting (persistence) | Persistence | 🟢 Blocked | Channel allowlist in `check_permissions` |
| SAFE-T1601 | System prompt disclosure | Discovery | 🟢 Blocked | Verbatim fragment & key detection in `filter_final_response` |
| SAFE-T1102 | Indirect injection via retrieved content | Execution | 🟢 Blocked | In-band redaction in `filter_tool_result` + channel allowlist |
| SAFE-T1501 | Cross-tool PII harvesting | Collection | 🟢 Blocked | Stateful session call budget in `check_permissions` |

Status key: 🔴 Undefended → 🟡 Partially mitigated → 🟢 Blocked (with test)

## Defense Architecture in `middleware.py`

The guardrail layer intercepts agent actions across three interception points:

1. **Pre-Tool Dispatch (`guardrail_check`)**:
   - `validate_input`: Enforces strict Pydantic v2 schemas (`CustomerIdInput`, `WikiQueryInput`, `SlackMessageInput`). Rejects SQL injection payloads and path traversal attempts (`../`) before any backend execution.
   - `check_permissions`: Enforces channel allowlist (`#billing`, `#support`, `#general`), disallowing untrusted exfiltration destinations (`#attacker-dump`, `#external-reports`). Enforces a stateful session call budget (maximum 3 customer record lookups per multi-turn session) preventing mass PII harvesting.
   - `filter_output`: Inspects tool arguments destined for outbound sinks, matching sensitive patterns (credit cards, API keys, passwords, SSNs).

2. **In-Band RAG Sanitization (`filter_tool_result`)**:
   - Inspects content returned from external sources (wiki queries, document searches) before it enters the LLM's conversation history. Replaces known injection markers (e.g. `[SYSTEM INSTRUCTION]`, `OVERRIDE:`, exfiltration directives) with `[REDACTED: suspicious injection directive removed]`.

3. **Post-Reasoning Output Redaction (`filter_final_response`)**:
   - Sanitizes the agent's final natural language response to the user. Scans for credential patterns (`_SECRET_KEY_RE`) and verbatim system prompt instruction disclosures (`_SYSTEM_PROMPT_LEAK_RE`), replacing compromised replies with an explicit security block message.

## Out of scope

- Network-layer attacks (the system is entirely local, no external network).
- Model weight tampering (Ollama manages the model files; trust boundary is
  the API surface at `localhost:11434`, not the weights themselves).
- Attacks against the evaluation harness itself — `agenteval/` is a measurement
  tool, not a target.
