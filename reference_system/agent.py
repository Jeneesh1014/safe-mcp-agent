"""
LangGraph orchestrator — the agent brain.

Responsibilities (Week 3):
  - Graph definition: nodes for reasoning + tool execution
  - Takes a natural-language request and chooses which tool(s) to call
  - Chains 2+ tool calls in sequence for multi-step requests
    e.g. "look up customer 4471 and send them their balance"
  - OpenTelemetry spans hooked into LangGraph callbacks so every LLM
    call and tool call gets traced to traces.db

Week 3 acceptance: run 5-10 varied prompts manually and confirm the agent
behaves sensibly before moving to red-teaming (ROADMAP.md Week 4).
"""
# TODO(week-3): implement LangGraph agent
