# Agent Instructions & Operating System

This repository uses an agent operating system consisting of structured foundation documentation in `docs/` and a dynamic, living memory in `MEMORY.md`. Follow this routine on every task.

---

## Startup Routine

Before answering complex questions, proposing plans, or writing/modifying code:

1. **Read Foundation in `docs/`**
   The `docs/` directory is the single source of truth for the project vision, technical architecture, and standards. Always consult the relevant document:
   - [docs/PROJECT.md](file:///Users/MAC/Desktop/PROJECTS/safe-mcp-agent/docs/PROJECT.md): **Entry point. Read this first.** Explains the two products in this repo (the `safe-mcp-agent` application and the standalone `agenteval`/`mcp-guardeval` library), why the project exists, and the 4-part architecture (Target, Brain, Shield, Ruler).
   - [docs/ARCHITECTURE.md](file:///Users/MAC/Desktop/PROJECTS/safe-mcp-agent/docs/ARCHITECTURE.md): Component interactions, data flow, LangGraph structure, guardrail pipeline, and SQLite telemetry.
   - [docs/CONVENTIONS.md](file:///Users/MAC/Desktop/PROJECTS/safe-mcp-agent/docs/CONVENTIONS.md): Coding rules, strict Conventional Commits (`feat`, `fix`, `test`, etc.), code comments policy (explain *why*, not *what*), and formatting standards.
   - [docs/ROADMAP.md](file:///Users/MAC/Desktop/PROJECTS/safe-mcp-agent/docs/ROADMAP.md): Project roadmap, milestones, and phased deliverables.
   - [docs/THREAT_MODEL.md](file:///Users/MAC/Desktop/PROJECTS/safe-mcp-agent/docs/THREAT_MODEL.md): Catalogued attack surfaces, threat vectors, and guardrail defense requirements.

2. **Read `MEMORY.md`**
   Read [MEMORY.md](file:///Users/MAC/Desktop/PROJECTS/safe-mcp-agent/MEMORY.md) at the repository root. This tracks:
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

---

## Karpathy-Inspired Coding Guidelines

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

### 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

### 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

### 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

### 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.
