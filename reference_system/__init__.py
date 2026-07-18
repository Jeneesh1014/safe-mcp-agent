"""
reference_system — the agent under test.

This package contains three modules:
  - mcp_server   : the MCP server exposing mock enterprise tools
  - middleware    : guardrail interception layer (sits between agent and server)
  - agent         : LangGraph orchestrator that drives tool selection

Import only what's needed. Avoid importing anything from agenteval/ here —
that boundary must stay clean so agenteval stays independently installable.
"""
