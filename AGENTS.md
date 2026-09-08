# Agent Instructions & Operating System

This repository uses an agent operating system consisting of structured foundation documentation in `docs/` and a dynamic, living memory in `MEMORY.md`. Follow this routine on every task.

---

## Startup Routine

Before answering complex questions, proposing plans, or writing/modifying code:

1. **Read Foundation in `docs/`**
   The `docs/` directory is the single source of truth for the project vision, technical architecture, and standards. Always consult the relevant document:
   - [docs/PROJECT.md](file:///Users/MAC/Desktop/J/PROJECTS/safe-mcp-agent/docs/PROJECT.md): **Entry point. Read this first.** Explains the two products in this repo (the `safe-mcp-agent` application and the standalone `agenteval`/`mcp-guardeval` library), why the project exists, and the 4-part architecture (Target, Brain, Shield, Ruler).
   - [docs/ARCHITECTURE.md](file:///Users/MAC/Desktop/J/PROJECTS/safe-mcp-agent/docs/ARCHITECTURE.md): Component interactions, data flow, LangGraph structure, guardrail pipeline, and SQLite telemetry.
   - [docs/CONVENTIONS.md](file:///Users/MAC/Desktop/J/PROJECTS/safe-mcp-agent/docs/CONVENTIONS.md): Coding rules, strict Conventional Commits (`feat`, `fix`, `test`, etc.), code comments policy (explain *why*, not *what*), and formatting standards.
   - [docs/ROADMAP.md](file:///Users/MAC/Desktop/J/PROJECTS/safe-mcp-agent/docs/ROADMAP.md): Project roadmap, milestones, and phased deliverables.
   - [docs/THREAT_MODEL.md](file:///Users/MAC/Desktop/J/PROJECTS/safe-mcp-agent/docs/THREAT_MODEL.md): Catalogued attack surfaces, threat vectors, and guardrail defense requirements.

2. **Read `MEMORY.md`**
   Read [MEMORY.md](file:///Users/MAC/Desktop/J/PROJECTS/safe-mcp-agent/MEMORY.md) at the repository root. This tracks:
   - What has been learned across sessions.
   - Active tasks, current sprint state, and blockers.
   - User corrections, feedback, and preferred working habits.
   - Environment and tooling quirks.

3. **Synthesize and Execute**
   Use the foundation in `docs/` together with the state in `MEMORY.md` to shape every task, plan, and code change.

---

## Dynamic Memory System

Keep [MEMORY.md](file:///Users/MAC/Desktop/J/PROJECTS/safe-mcp-agent/MEMORY.md) current at all times.

### When to update `MEMORY.md`:
- When the user corrects your output, tone, architectural approach, or workflow.
- When a new project decision, milestone, or task status changes.
- When an environment, dependency, or tooling quirk is discovered.

### How to update `MEMORY.md`:
- **Update in place**: Replace outdated info rather than just appending below it. The file must always reflect the single latest source of truth.
- **Categorize accurately**:
  - **Voice**: Tone, phrasing, response length, and communication style.
  - **Process**: Workflow expectations, testing gates, commit handling, and plan approvals.
  - **Projects**: Active work, current state, completed items, and roadblocks.
  - **Tools**: CLI commands, Poetry quirks, test commands, paths, and environment variables.
  - **Decisions & Corrections**: Architectural choices, rejected alternatives, and explicit corrections from the user.
