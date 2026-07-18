"""
Attack script: SAFE-T1203 — Tool Argument Hijacking / Parameter Overloading.

Technique summary:
  Malformed or oversized arguments are passed to a tool with the intent of
  overloading parameter parsing, bypassing validation, or causing the tool
  to operate outside its intended scope.

Week 4 target:
  1. Run this against the UNDEFENDED agent and confirm the malformed call
     reaches the MCP server without being rejected.
  2. Re-run after middleware (Week 5) and confirm strict Pydantic validation
     rejects the call before it reaches the server.

Usage:
    python attacks/safe_t1203_tool_hijack.py
"""
# TODO(week-4): implement attack script
