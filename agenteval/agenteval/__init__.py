"""
agenteval — automated evaluation library for MCP-based LLM agents.

Published to PyPI as `mcp-guardeval` (pip install mcp-guardeval).
Importable as `import agenteval`.

Sub-modules:
  telemetry/trace_processor  normalises OTel spans into flat SQLite rows
  metrics/task_success        did the agent complete the task
  metrics/security            did an attack get through
  plugin                      pytest plugin — hooks for --agenteval
  storage                     SQLite read/write layer

This package must stay independently installable. It must not import
anything from reference_system/ at module load time.
"""
