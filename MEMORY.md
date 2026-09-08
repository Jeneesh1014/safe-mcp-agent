# Memory

*Last Updated: 2026-09-06*

This file is maintained dynamically across agent sessions. Keep this file updated in-place whenever instructions, preferences, project status, or corrections occur.

---

## Voice & Interaction
- **Tone**: Direct, concise, technical, and collaborative.
- **Style**: Avoid unnecessary fluff or boilerplate preamble. Explain technical rationale ("why") when making recommendations.

---

## Process & Workflow
- **Foundational Context**: Always check `docs/` (`PROJECT.md`, `ARCHITECTURE.md`, `CONVENTIONS.md`, `ROADMAP.md`, `THREAT_MODEL.md`) before proposing changes or writing code.
- **Commits**: Strict Conventional Commits (`feat(scope):`, `fix(scope):`, etc.) as documented in `docs/CONVENTIONS.md`.
- **Verification**: Always verify changes with tests or dry runs before concluding a task.

---

## People & Roles
- **User**: Lead engineer / project owner. Drives project vision, reviews architecture, and steers roadmap.
- **Agent**: Pair programmer. Follows conventions, reads documentation first, maintains living memory, and writes robust, well-tested code.

---

## Projects & Current Status
- **Repository**: `safe-mcp-agent`
- **Dual Deliverables**:
  1. `safe-mcp-agent`: The application (Target MCP server, LangGraph agent brain, security shield/guardrails, telemetry).
  2. `agenteval` / `mcp-guardeval`: Standalone evaluation harness package intended for independent PyPI release.
- **Current Phase**: Initial setup, foundational documentation, agent instructions, and architecture scaffolding.

---

## Output Preferences
- Format with GitHub Flavored Markdown.
- Use clickable `file://` links for file paths and specific code symbols whenever referencing files.

---

## Tools & Environment
- **Platform**: macOS (zsh).
- **Python Stack**: Poetry-managed environment.
- **Telemetry**: SQLite (`traces.db`).
- **Knowledge Base**: OpenKB (`wiki/`).

---

## Corrections & Learned Decisions
*(In-place log: update directly when corrections or new decisions are made.)*
- **Agent Operating Routine**: Configured `AGENTS.md` and `MEMORY.md` at repository root so the agent routinely reviews `docs/` and updates memory in place when corrected or when context evolves.
