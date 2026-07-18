"""
Guardrail middleware — intercepts every tool call before it reaches the MCP server.

Responsibilities (Week 5):
  - Input validation against strict Pydantic schemas
  - Permission scoping: each call is checked against a defined scope,
    not assumed to have blanket access
  - Output filtering: block sensitive-looking data from flowing into
    outbound tools (send_slack_message)
  - Structured logging of every block: technique ID (if known), tool
    name, timestamp, decision

A block that isn't logged doesn't exist in production. Don't build silent drops.

SAFE-MCP technique IDs this module is expected to block once implemented:
  - SAFE-T1201: prompt injection to hijack tool selection
  - SAFE-T1203: tool argument hijacking / parameter overloading
  - SAFE-T1208: indirect data exfiltration via a downstream tool
"""
# TODO(week-5): implement guardrail middleware
