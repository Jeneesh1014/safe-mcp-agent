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

| Technique ID | Name | Status | Mitigation in `middleware.py` |
|---|---|---|---|
| SAFE-T1201 | Prompt injection — tool hijack | 🔴 Undefended (Week 3) | TODO(week-5) |
| SAFE-T1203 | Tool argument hijacking | 🔴 Undefended (Week 3) | TODO(week-5) |
| SAFE-T1208 | Indirect data exfiltration | 🔴 Undefended (Week 3) | TODO(week-5) |

Status key: 🔴 Undefended → 🟡 Partially mitigated → 🟢 Blocked (with test)

## Out of scope

- Network-layer attacks (the system is entirely local, no external network).
- Model weight tampering (Ollama manages the model files; trust boundary is
  the API surface at `localhost:11434`, not the weights themselves).
- Attacks against the evaluation harness itself — `agenteval/` is a measurement
  tool, not a target.
