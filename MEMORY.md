# Memory

*Last Updated: 2026-09-11*

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
- **Current Phase**: Completed and released! `mcp-guardeval` v0.2.0 published on PyPI with configurable pytest plugin (`guardeval_techniques`, `guardeval_log`, `guardeval_traces_db`, `guardeval_block_threshold` via `pyproject.toml`), technique auto-discovery from guardrail logs, `summary()` convenience methods on result types, and a professional README written for external adopters. Full 8-week roadmap + post-release polish completed.

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
- **Karpathy-Inspired Guidelines**: Consolidated in [AGENTS.md](file:///Users/MAC/Desktop/PROJECTS/safe-mcp-agent/AGENTS.md) alongside the startup routine and memory system (CLAUDE.md removed to keep a single comprehensive file).
- **No AI-style code**: No decorative dashes/separators (`---`, `# ----`), no filler comments that restate the code, no unnecessary abstractions. Keep code lean. Comments explain *why* only.
- **Guardrail In-Band & Error Hardening**: Final agent natural-language responses are filtered for credentials and system prompt disclosures; blocked tool executions return generic error messages to the LLM to prevent prompt injection feedback loops.
- **Session Call Budget Persistence**: `run(prompt, session=...)` accepts and threads an explicit `Session` across multi-turn queries to prevent per-turn budget resets.
- **AgentEval Metric Accuracy**: `score_security_run` only assigns `PARTIAL` when tool errors are directly tied to that technique, preventing unrelated errors from degrading the block rate.
- **Ollama Generation Safeguards for Sub-3B Models**: Sub-3B models like `llama3.2:1b` can enter infinite token generation loops under adversarial prompt injections without emitting an end-of-turn token. Set `num_predict=1024` on `ChatOllama` and `recursion_limit=10` on LangGraph `invoke` to bound execution.
- **Dynamic Trace DB Routing**: `_SQLiteSpanExporter` connects to `_TRACES_DB` on each `export()` call, allowing test and benchmark harnesses to isolate traces per model without encountering OpenTelemetry's TracerProvider lock.
- **Tool Argument Type Coercion (`str | int`)**: Quantized local LLMs (e.g. Ollama models) often emit numeric IDs like `4471` as JSON integers instead of strings. Defining tool signatures as `customer_id: str | int` ensures LangChain schema validation succeeds before internal string coercion.
- **Verbatim Fragment Leak Detection**: LLMs leaking system prompts often emit intermediate phrases (e.g. "use the tools in the right order and chain the results", "Always prefer query_openkb_wiki...") rather than the first sentence. `_SYSTEM_PROMPT_LEAK_RE` checks distinctive structural phrases across the entire system prompt.
- **Clean-Checkout Reproducibility & Unstaged State**: `reference_system/fixtures/customers.db` is un-ignored in `.gitignore` (`!reference_system/fixtures/customers.db`), and `mcp-guardeval` is declared as an editable path dependency (`mcp-guardeval = {path = "agenteval", develop = true}`). Note: Seed fixtures (`customers.db`), `wiki/`, benchmark scripts, and Docker files are currently untracked/uncommitted pending explicit user staging instructions.
- **Poetry Lock Tracking**: Removed `poetry.lock` from `.gitignore` so lockfile updates are version-controlled rather than silently ignored.
- **Docker Compose Volume Directory Prevention**: Configured `docker-compose.yml` to bind mount directory `./traces:/app/traces` and set `TRACES_DB=/app/traces/traces.db` rather than mounting `./traces.db` directly as a file. This prevents Docker from creating `traces.db` as a folder on clean hosts where `traces.db` does not yet exist.
- **Package Metadata Normalization**: Set official package author metadata across both `pyproject.toml` and `agenteval/pyproject.toml` to `Jeneesh Surani <jeneeshsurani@gmail.com>`, matching repo license and git identity before PyPI publishing.
- **Project Education & Interview Documentation**: Created a complete suite of root-level educational guides with recruiter/staff-engineer Q&A, architectural breakdowns, problem retrospectives, and flashcards covering the full 8-week lifecycle: `WEEK_1_2_DEEP_DIVE.md` (scaffolding, fixtures, OpenKB, MCP server), `WEEK_3_DEEP_DIVE.md` (LangGraph orchestrator, cyclical state machine, local Ollama tool calling, OpenTelemetry SQLite tracing), `WEEK_4_DEEP_DIVE.md` (Red Team attack suite, 7 SAFE-MCP techniques, empirical vulnerability baselines, forensic side-effect verification), `WEEK_5_DEEP_DIVE.md` (Guardrail middleware shield, Pydantic input validation, permission scoping, outbound PII leak filtering, recursive inbound document sanitization, egress response filtering), `WEEK_6_DEEP_DIVE.md` (The Ruler evaluation harness, `mcp-guardeval` PyPI standalone package, OpenTelemetry span extraction, deterministic task success & security scoring, pytest plugin integration), `WEEK_7_8_DEEP_DIVE.md` (Cross-model benchmarking 3B vs 1B, OpenKB vs flat wiki, Docker Metal GPU host networking, PyPI release, and master graduation summary), and `RESUME_TO_INTERVIEW_MASTER.md` (Production resume project section, 10 rigorous interrogation questions, 4-part Context/Ownership/Reasoning/Evidence answers, and 10 grilling trap follow-ups).
