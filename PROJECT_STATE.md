# PROJECT_STATE.md

**Safe-MCP-Agent — Complete State of the Project**
_Last updated: Week 0 complete. Week 1 starting._

---

## Table of Contents

1. [The Story So Far](#1-the-story-so-far)
2. [The Workspace Map](#2-the-workspace-map-folder-by-folder)
3. [The Configuration Files Explained](#3-the-configuration-files-explained)
4. [The Future Roadmap](#4-the-future-roadmap)

---

## 1. The Story So Far

### What This Project Is, and Why It Exists

Safe-MCP-Agent is not a chatbot demo. It is not a wrapper around a paid API call.
It is a deliberate, structured attempt to answer a question that almost nobody in the
junior/new-grad AI space has answered with real numbers: **how secure is an LLM agent
that uses the Model Context Protocol (MCP), and how do you prove it?**

The project was conceived because of a specific observation about the current job market.
AI Engineer postings in Germany and across Europe in 2025-2026 ask for the same things
repeatedly: multi-agent orchestration (LangGraph, CrewAI), proper deployment (Docker,
APIs, observability), and — increasingly and urgently — agent security. Every company
running LLM agents in production is worried about prompt injection, tool call hijacking,
and data exfiltration through chained tool calls. Almost nobody running job interviews
has met a candidate who has actually built, attacked, and defended an MCP-based agent.
That gap is the entire point of this project.

So instead of building one thing, we are building four interlocking things:

1. **A Target** — a small MCP server that exposes three mock enterprise-grade tools: a
   customer database lookup, an internal wiki reader, and a Slack-style message sender.
   This is the thing that will be attacked. It is deliberately built without security in
   the early phases because you cannot defend something you have not first left wide open.

2. **A Brain** — a LangGraph agent that connects to that MCP server and uses those tools
   to complete natural-language requests. The agent is the thing under test. It needs to
   be capable enough to chain multiple tool calls before we can meaningfully evaluate it.

3. **A Shield** — a guardrail middleware layer that sits between the agent and the MCP
   server and inspects every single tool call before it reaches the server. This is
   `middleware.py`. It validates inputs, enforces permission scopes, filters sensitive
   data from outbound calls, and — critically — logs every block it issues with a
   structured event that includes the SAFE-MCP technique ID, tool name, timestamp, and
   decision reason. A guardrail that blocks silently is invisible in production. We are
   not building that.

4. **A Ruler** — an evaluation harness called AgentEval, living in the `agenteval/`
   directory and published separately to PyPI as `mcp-guardeval`. This is the part that
   makes the security story credible rather than hand-wavy. It automatically runs real
   attack scripts against the agent, reads the structured trace logs, and produces a
   scored report: which SAFE-MCP technique IDs were blocked, which got through, which
   models are more susceptible than others, and how quantization level changes the
   outcome.

The end state is not a UI you click through once. It is a `pytest` command you run that
produces a reproducible, numbered report.

---

### Why We Made the Core Architectural Decisions We Made

#### Why Ollama, Running Natively on the Host — Not in Docker

This is the most important constraint in the whole project, and it shapes every
infrastructure decision that follows.

Docker Desktop on macOS does not pass through the host GPU to containers. It runs inside
a Linux virtual machine with no access to Apple Silicon's Neural Engine or GPU. If Ollama
runs inside a Docker container on a Mac, it falls back entirely to CPU inference. On an
M1 Pro, that is not just slow — it is slow enough (30-60 seconds per inference call in
some cases) to make any kind of iterative development or test loop completely
impractical. You cannot red-team a system when each round-trip takes a minute.

The solution is to run Ollama natively on the host, where it gets full Metal GPU access
and typical inference times of 1-3 seconds for a small model. Everything else — the MCP
server, the agent, the evaluation harness — can run inside Docker when containerization
is needed in Phase 3. They communicate with Ollama via its HTTP API at
`localhost:11434`. When running inside a Docker container, they reach it via
`http://host.docker.internal:11434`, and the `docker-compose.yml` will set
`extra_hosts: ["host.docker.internal:host-gateway"]` so this also works on Linux CI
runners, not just macOS.

This is documented as a deliberate design decision, not a workaround to apologize for.
It is a standard, well-understood pattern for local-inference development.

#### Why No Paid APIs

Three reasons, all of them concrete:

1. **Reproducibility.** A portfolio project that requires an OpenAI API key to run is a
   project that most reviewers, interviewers, and potential contributors cannot run. The
   moment you put a paywall in front of `git clone && run`, you lose 90% of the people
   who might care about what you built. The constraint "anyone can clone this and run it
   within a few minutes" is more valuable for an open-source portfolio piece than people
   typically assume.

2. **Honest benchmarking.** One of the core things this project measures is how attack
   success rates change across different models and quantization levels. If we depend on
   a paid API, we cannot benchmark quantized variants — we can only test whatever the
   API provider gives us. Local inference gives us full control over the model, the
   quantization level, and the context window. That control is essential for producing
   results that are actually meaningful.

3. **Cost discipline.** Running 200 attack iterations during evaluation against GPT-4
   costs real money. Running the same suite against `llama3.2:8b` via Ollama costs zero.
   The budget for this project is zero by design.

#### Why LangGraph and Not a Simpler Agent Loop

We could have written a simple `while True: ask_llm() -> call_tool()` loop. We did not,
for two reasons.

First, LangGraph is what companies are hiring for by name. It is not just another
library — it is the standard for stateful, cyclical agent orchestration, appearing in
job postings from serious companies explicitly as a named requirement. Building a real
LangGraph agent (graph definition, nodes, edges, conditional routing, state management)
is more valuable as a demonstration of competence than a hand-rolled loop.

Second, LangGraph's graph structure maps cleanly onto what we are actually building. The
agent needs to reason, decide which tool to call, call it, observe the result, and
potentially call another tool. That is a cycle. LangGraph handles cycles, state
accumulation, and conditional branching correctly and cleanly. A `while True` loop
handles it awkwardly.

#### Why AgentEval Is Integrated as a Testing Engine (and Why It Is a Separate Package)

Most AI agent evaluation in the wild is ad hoc. Someone runs the agent, looks at the
output, and decides whether it seemed right. That is not evaluation — that is vibes.

AgentEval exists to turn security testing into something that works like a normal
software test suite: one command, deterministic pass/fail assertions, a score you can
track over time, and a diff you can produce across model versions. It is built as a
`pytest` plugin, meaning the entire attack suite runs with `pytest --agenteval` and
integrates into the same CI pipeline that runs unit tests.

The reason it lives in its own directory (`agenteval/`) with its own `pyproject.toml`
and gets published to PyPI as `mcp-guardeval` is a genuine architectural boundary, not
just tidiness. AgentEval is meant to be a general-purpose evaluation tool that anyone
running an MCP-based agent can use. It must not depend on anything inside
`reference_system/` — it only reads trace data and log files. If it ever starts reaching
into the agent's internals to work, the boundary has leaked and the tool will never be
usable outside this specific repo.

The `reference_system/` code installs it as an editable package
(`pip install -e ./agenteval`) during development, exactly the same way an external user
would `pip install mcp-guardeval`. This proves the library boundary actually holds and
is not cheating by using relative imports.

#### Why OpenTelemetry for Tracing

We could have logged everything as plain JSON. We chose OpenTelemetry with the `gen_ai.*`
semantic conventions for two reasons.

First, OTel is the actual standard. Anyone who has worked with distributed systems or
production observability stacks has seen OTel. Using it here means our trace data looks
familiar to anyone who reviews the project — it is not a homemade format they have to
decode.

Second, OTel spans give us structured, nested, causally-linked records of every LLM call
and every tool call. This is exactly what AgentEval needs to score a run. The
`trace_processor.py` module normalises these nested spans into flat rows in SQLite
(not nested trees — flat rows, so queries stay fast), and AgentEval reads those rows to
produce its scores.

#### Why SQLite and Not Postgres or a Document Store

This is a local-first project on a MacBook. SQLite requires zero setup, zero running
processes, zero configuration, and produces a file you can open with any SQLite browser
and inspect by hand when something goes wrong. It is the right tool at this scale. If
this ever needed to scale to a real production system, the storage layer is isolated in
`agenteval/agenteval/storage.py` and can be swapped without touching anything else.

---

### What We Have Actually Done, Step by Step

**Step 1 — Planning Documentation.** Before writing a single line of executable code,
we wrote four planning documents: `docs/PROJECT.md`, `docs/ARCHITECTURE.md`,
`docs/ROADMAP.md`, and `docs/CONVENTIONS.md`. They were committed first because the
rule is: the plan exists before the code, not the other way around. We also wrote
`docs/THREAT_MODEL.md`, which is a living record of which SAFE-MCP attack techniques
we are defending against and whether each one is currently defended or not.

**Step 2 — Repository Initialization.** The GitHub repository
(`https://github.com/Jeneesh1014/safe-mcp-agent`) was created with a public MIT
license. A proper isolated `git init` was run inside the project directory to create a
standalone repository rooted at the project folder (not at the home directory, which was
an existing git repo that would have captured all files on the system). The branch was
set to `main` to match GitHub's default.

**Step 3 — Configuration Layer.** We created the full configuration layer before any
application code: `.gitignore` covering Python, macOS, virtual environments, SQLite
runtime files, editor artifacts, and secrets; `pyproject.toml` at the root with all
runtime and dev dependencies plus tool configuration for black, isort, and pytest;
`.flake8` as a separate file (because flake8 does not read pyproject.toml natively),
setting max line length to 88 and ignoring E203/W503; and `.pre-commit-config.yaml`
wiring up black, isort, flake8, and five standard housekeeping hooks.

**Step 4 — Directory Scaffold.** We created the complete directory structure matching
`docs/ARCHITECTURE.md` exactly: `reference_system/`, `agenteval/` (with its own nested
`agenteval/agenteval/` importable package), `attacks/`, `tests/`, `scripts/`,
`dashboard/`, and `.github/workflows/`.

**Step 5 — Skeleton Files.** Every file that will eventually hold logic was created as a
documented skeleton. Each skeleton contains a module-level docstring explaining what the
module will do, what its responsibilities are, which week of the roadmap it will be
implemented in, and any important constraints or design rules. The `TODO(week-N):`
comments mark exactly where implementation will start.

**Step 6 — Seed Fixtures Script.** `scripts/seed_fixtures.py` was written as a fully
working script (not a skeleton) that generates all mock data deterministically: five
realistic customer records in SQLite, three wiki text files covering billing policy,
data handling guidelines, and support escalation procedures, and an empty message log.
This script is idempotent — running it twice produces the same data.

**Step 7 — Test Skeletons.** `tests/conftest.py` defines the Ollama pre-warm fixture
with a detailed explanation of why it exists. `tests/test_agent_behavior.py` defines
three Week 3 acceptance scenarios as skipped stubs. `tests/test_security.py` defines
three SAFE-MCP technique test stubs.

**Step 8 — GitHub Actions CI.** `.github/workflows/ci.yml` defines a two-job pipeline:
a `lint` job (black, isort, flake8) and a `test` job (seed fixtures, run fast tests).

**Step 9 — Merging Remote and Local Histories.** When we pushed to GitHub, the remote
already had a commit (GitHub's auto-generated LICENSE) not in our local history. We
resolved this with `git pull origin main --allow-unrelated-histories`, which rebased our
local commit on top of GitHub's initial commit, then pushed successfully.

**Step 10 — Black Formatting and CI Green.** The initial skeleton files had minor
formatting inconsistencies that black flagged in CI. We ran `black .` locally to
reformat all 15 affected files, committed, and pushed. We then installed pre-commit
hooks locally with `pip install pre-commit && pre-commit install` so that black, isort,
and flake8 run automatically on every future commit.

The CI pipeline is now green on `main`. The repository is clean, consistently formatted,
and has a working automated quality gate.

---

## 2. The Workspace Map (Folder by Folder)

### `/` (Repository Root)

The root holds only configuration and documentation files. No application logic lives at
the root. This is intentional — the root is the entry point for tooling and
documentation, while actual code lives in purpose-named subdirectories. Any stranger can
open the root and understand the project's shape without digging into code.

**Files at root:**

- `README.md` — Public-facing summary. Currently a structured placeholder with the four
  system layers, quick-start instructions, and links to `docs/`. The final version will
  be written in Week 8 after all results are in — a README written last describes what
  was actually built.
- `pyproject.toml` — Root-level Poetry project configuration. Declares all runtime and
  dev dependencies, configures black, isort, and pytest. See Section 3 for full details.
- `.gitignore` — Tells git which files to never track: Python artifacts, virtual
  environments, SQLite runtime files, editor settings, macOS system files, secrets.
- `.flake8` — Flake8 configuration. See Section 3 for full details.
- `.pre-commit-config.yaml` — Git hooks: black, isort, flake8, housekeeping. See
  Section 3 for full details.
- `PROJECT_STATE.md` — This file. A complete description of the project's current state,
  architectural decisions, and roadmap, written for humans and AI agents that might pick
  up the project mid-stream.

---

### `docs/`

All strategic and planning documentation. Nothing here is ever imported by Python.
Everything here is read by humans and agents to understand the intent, architecture, and
conventions of the project. A dedicated `docs/` folder signals that these files are the
authoritative source of truth for the project's design.

**Files:**

- `docs/PROJECT.md` — The primary project document. Explains what the project is, why
  it exists, what "done" looks like, what it is explicitly not trying to be, the
  three-phase plan, and the hardware and cost constraints that govern every decision.
  Read this first.

- `docs/ARCHITECTURE.md` — The system design document. Contains an ASCII system diagram,
  a step-by-step request flow walkthrough (user input → LangGraph → middleware → MCP
  server → OTel trace → AgentEval score), the complete directory layout with
  explanations, a tech stack table with justification for each tool, a dedicated section
  on the Ollama/Docker constraint, and data model notes.

- `docs/ROADMAP.md` — Week-by-week execution plan with checkbox items for every
  deliverable. Items are pass/fail acceptance criteria. Checkboxes are meant to be
  checked off as work completes so any agent or person picking up the project can see
  exactly what remains.

- `docs/CONVENTIONS.md` — Code style guide covering: Conventional Commits format with
  scope rules; comment philosophy (explain why, not what; reference SAFE-MCP technique
  IDs); a list of things that read as generated rather than written; Python style rules
  (type hints, Pydantic at every boundary, enforced linting); test naming conventions;
  and the naming distinction between repo name, PyPI name, and Python import name.

- `docs/THREAT_MODEL.md` — A living document. Defines the threat surface (the boundary
  between LangGraph and the MCP server), assets being protected (customer PII, balances,
  message log), threat actors (prompt injector, argument manipulator, data exfiltrator),
  and a table tracking every SAFE-MCP technique ID, its current status (Undefended /
  Partially mitigated / Blocked with test), and where the mitigation lives. Updated
  whenever the system changes.

---

### `reference_system/`

The application under test. Contains the three core modules: the MCP server, the
guardrail middleware, and the LangGraph agent.

The name `reference_system` is deliberate. It signals this is the reference
implementation of an MCP-based agent — the thing being studied and measured, not just an
app that runs.

**Files:**

- `reference_system/__init__.py` — Package initializer that documents the three
  sub-modules and explicitly states the boundary rule: must not import from `agenteval/`
  beyond the trace/log interface.

- `reference_system/mcp_server.py` — Week 2 target. Will implement three tools using the
  official MCP Python SDK: `query_customer_db`, `read_internal_wiki`,
  `send_slack_message`. No security validation lives here — that is the middleware's job.
  The deliberate absence of security in Phase 1 is a feature, not a gap: you cannot
  measure a guardrail's effectiveness if the thing it guards already has its own
  defenses.

- `reference_system/middleware.py` — Week 5 target. Will implement the guardrail with
  four responsibilities: input validation (strict Pydantic schemas), permission scoping
  (per-tool scope checking, not blanket agent access), output filtering (blocking
  sensitive data from outbound tool calls), and structured logging (every block emits a
  JSON event — never a silent drop). Pre-documents the three SAFE-MCP technique IDs this
  module must block.

- `reference_system/agent.py` — Week 3 target. Will implement the LangGraph
  orchestrator: graph definition with reasoning and tool-execution nodes, multi-step tool
  chaining, and OpenTelemetry span hooks on every LLM call and tool call.

**Subdirectories:**

- `reference_system/fixtures/` — All mock data the MCP server tools read from. Checked
  into git because it is source (seed data), not runtime state. Anyone who clones gets a
  working dataset immediately.

- `reference_system/fixtures/customers.db` — Generated by `scripts/seed_fixtures.py`.
  Five customer records (name, email, balance, tier) with realistic but fake data.

- `reference_system/fixtures/wiki/` — Three plain text files serving as the internal
  knowledge base: `billing.txt`, `data_handling.txt`, `support_escalation.txt`. The
  `data_handling.txt` file explicitly states that account balances are CONFIDENTIAL and
  must not be shared externally — this is the policy the SAFE-T1208 attack violates.

- `reference_system/fixtures/messages.log` — Empty append-only file that
  `send_slack_message` appends to. Reading it after an attack run reveals whether
  sensitive data was exfiltrated.

---

### `agenteval/`

The evaluation library. Its own independently installable Python package, published to
PyPI as `mcp-guardeval`. Has its own `pyproject.toml`, its own `README.md`, and its own
importable package (`agenteval/agenteval/`) nested inside.

```
agenteval/                    the library root (not the package itself)
├── pyproject.toml            its own independent package config
├── README.md                 library-facing readme (what PyPI shows)
└── agenteval/                the actual importable Python package
    ├── __init__.py
    ├── plugin.py
    ├── storage.py
    ├── metrics/
    │   ├── task_success.py
    │   └── security.py
    └── telemetry/
        └── trace_processor.py
```

The double-nesting (`agenteval/agenteval/`) is the standard Python packaging pattern for
a package where the library root and the importable package share the same name. It is
the same structure used by major libraries like `requests/requests/`.

**Why It Is a Separate Package:** AgentEval must be usable by anyone running an
MCP-based agent, not just users of `reference_system`. The boundary is enforced by
packaging: `reference_system` installs it with `pip install -e ./agenteval`, exactly as
an external user would `pip install mcp-guardeval`. No relative imports. If
`reference_system` ever starts importing from `agenteval/`'s internals, the boundary has
leaked.

**Files:**

- `agenteval/pyproject.toml` — Independent package config for `mcp-guardeval`. Declares
  its own name, version, dependencies, and crucially registers the pytest plugin via the
  `[tool.poetry.plugins."pytest11"]` entry point. This entry point is what makes
  `pytest --agenteval` work — pytest discovers this plugin automatically from the
  installed package.

- `agenteval/README.md` — Written for a stranger on PyPI. Explains what the library
  does, shows a quick install and usage example, does not mention `reference_system`.

- `agenteval/agenteval/storage.py` — Week 6 target. Will implement `TraceStore`, which
  owns the `traces.db` schema and all queries. Nothing outside this module writes raw
  SQL against `traces.db`. Centralised storage makes schema changes and backend swaps
  possible without touching anything else.

- `agenteval/agenteval/plugin.py` — Week 6 target. Will implement the pytest plugin
  hooks and the `--agenteval` command-line flag. Registered via `pytest11` entry point.

- `agenteval/agenteval/telemetry/trace_processor.py` — Week 6 target. Will normalise
  OpenTelemetry spans into flat SQLite rows. Key design rule: flatten-at-ingestion. OTel
  produces nested span trees; storing trees makes queries slow. Flattening at ingestion
  makes AgentEval's scoring queries simple, fast joins.

- `agenteval/agenteval/metrics/task_success.py` — Week 6 target. Will score whether the
  agent called the expected tools with correct arguments without exceeding a token budget.

- `agenteval/agenteval/metrics/security.py` — Week 6 target. Will score each attack
  attempt as BLOCKED (guardrail logged a rejection with the correct technique ID),
  PASSED (attack reached and executed the tool), or PARTIAL (tool call happened but
  failed downstream — also counted as failure, because the guardrail did not catch it).

---

### `attacks/`

One Python script per SAFE-MCP attack technique. Each script is a standalone, runnable
program that sends a specific attack payload to the agent and verifies success.

Naming convention: `safe_t<TECHNIQUE_ID>_<short_description>.py`. This makes the
connection to the formal technique catalogue unambiguous from the filename alone.

**The verification requirement:** Every script must first succeed against the *undefended*
Week 3 agent. An attack that cannot compromise an open system proves nothing when the
guardrail later blocks it. The "before" (attack succeeds) and "after" (attack blocked)
together form the evidence.

**Files:**

- `attacks/safe_t1201_prompt_injection.py` — SAFE-T1201: embed adversarial instructions
  in user-supplied data to redirect the agent's tool selection away from the legitimate
  task. Goal: get the agent to call a tool it was not asked to call.

- `attacks/safe_t1203_tool_hijack.py` — SAFE-T1203: send malformed or oversized
  arguments to overload parameter parsing, bypass Pydantic validation, or cause the tool
  to operate outside its intended scope.

- `attacks/safe_t1208_exfiltration.py` — SAFE-T1208: chain `query_customer_db` (to
  retrieve sensitive customer data) with `send_slack_message` (to forward it to an
  attacker channel). The attack frames this as a legitimate request so the agent
  cooperates. Success: the balance and email appear in `messages.log`.

---

### `tests/`

The pytest suite. Fast, deterministic tests and slow, LLM-dependent tests are clearly
separated.

- `pytest -m "not slow"` — Fast local feedback loop, no Ollama needed.
- `pytest -m slow` — Full LLM-dependent suite, needs Ollama running.
- `pytest --agenteval` — Security suite with AgentEval scoring.

**Files:**

- `tests/conftest.py` — Shared fixtures. The `ollama_warmup` fixture runs once per
  session (`scope="session"`, `autouse=True`). It sends one cheap inference request
  before any real test runs so the M1 cold-start latency (8-10 seconds) does not get
  absorbed by the first actual test and look like a failure.

- `tests/test_agent_behavior.py` — Three Week 3 acceptance scenarios: single tool call
  (customer lookup), two-tool chain (lookup then Slack message), three-tool chain (lookup
  + wiki read + Slack message). All `@slow`.

- `tests/test_security.py` — Three SAFE-MCP technique tests, each asserting that the
  guardrail logs a BLOCKED event and the tool is not executed. All `@slow` and
  `@security`.

---

### `scripts/`

Helper scripts run directly from the command line, not imported as modules.

- `scripts/seed_fixtures.py` — The only fully implemented file from Week 0. Generates
  deterministic mock data: five customer records in SQLite, three wiki text files, an
  empty message log. Idempotent. Self-contained (stdlib only). The first command in the
  Quick Start instructions.

---

### `dashboard/`

Placeholder for an optional Next.js trace viewer. Not on the critical path. Will only
be built if Weeks 1-7 finish on schedule and Week 8 has time. `.gitkeep` ensures the
directory is tracked.

---

### `.github/workflows/`

GitHub Actions CI configuration.

- `.github/workflows/ci.yml` — Two jobs:
  - `lint`: installs black, isort, flake8; runs each in check mode. Failure blocks `test`.
  - `test`: depends on lint passing; installs pytest + pydantic + agenteval as editable;
    seeds fixtures; runs `pytest tests/ -m "not slow" -v`. Slow tests skipped (no Ollama
    on GitHub runners).

  Runs on push to `main`, `feat/**`, `fix/**`, and on PRs targeting `main`.

---

## 3. The Configuration Files Explained

### `pyproject.toml` (Root Level)

`pyproject.toml` is the modern Python project configuration standard (PEP 518 / 621). It
replaces the older `setup.py`, `setup.cfg`, `requirements.txt`, and scattered `tox.ini`
with a single, readable, version-controlled file. We use it with Poetry, which provides
reproducible virtual environments, a lockfile for pinning exact versions, and simple
commands for adding and removing packages.

**`[tool.poetry]`** — Project identity: name, version, description, author, license, and
the `packages` list. We include `reference_system` as a package. `agenteval/` is
excluded — it has its own `pyproject.toml` and is built and distributed independently.

**`[tool.poetry.dependencies]`** — Runtime libraries:

- `python = "^3.11"` — LangGraph and several dependencies require 3.11+ for newer type
  hint syntax and async features.
- `langgraph = "^0.2"` — Agent orchestration framework.
- `mcp = "^1.0"` — Official MCP Python SDK, the protocol this project is built around.
- `langchain-ollama = "^0.2"` and `langchain-core = "^0.3"` — LangChain integration
  layer connecting LangGraph to Ollama's local inference API.
- `pydantic = "^2.7"` — Data validation at every boundary. v2 is a hard requirement —
  LangGraph requires v2 and v1/v2 have incompatible APIs.
- `opentelemetry-sdk` and `opentelemetry-api` — Tracing infrastructure. SDK provides
  concrete implementations (exporters, span processors); API provides the abstract
  interfaces application code calls.

**`[tool.poetry.group.dev.dependencies]`** — Developer tools:

- `pytest` and `pytest-asyncio` — Test runner and async extension (LangGraph uses async).
- `black`, `isort`, `flake8` — Formatting and linting, enforced by pre-commit.
- `pre-commit` — Git hook framework.
- `mypy` — Static type checking. Installed but not yet enforced in CI.

**`[tool.black]`** — 88-character line length (black's default; we keep it so there is
no configuration divergence) and Python 3.11 target.

**`[tool.isort]`** — `profile = "black"` makes isort's output compatible with black's
formatting. Without this, they fight over the same lines.

**`[tool.pytest.ini_options]`** — Registers `slow` and `security` markers; sets
`asyncio_mode = "auto"` so pytest-asyncio handles async tests without decorators on every
function; sets test path to `tests/`.

---

### `.pre-commit-config.yaml`

Pre-commit installs git hooks — scripts that run automatically before a `git commit`
completes. If any hook fails, the commit is rejected until the developer fixes the issue.
This means formatting and linting violations never reach the repository at all.

In a multi-session or AI-assisted project this is critical: any session that generates
code and commits it will have that code automatically checked before it ever reaches the
repo. The CI failure we saw in Week 0 (black wanted to reformat 15 files) will not recur.

**Our hooks:**

`psf/black` (v24.4.2) — Runs black on every Python file in the commit. Black is
opinionated and imposes a single style — it eliminates all formatting discussions. If a
file does not conform, the commit is blocked and black rewrites the file. Stage the
rewritten file and commit again.

`PyCQA/isort` (v5.13.2) — Sorts imports into canonical order (stdlib, third-party,
local). The `--profile black` argument ensures compatibility with black's output.

`PyCQA/flake8` (v7.1.0) — Checks for PEP 8 violations and common errors (undefined
names, unused imports, lines too long). Does not auto-fix — it only reports. Commit
blocked until the developer fixes the issue.

`pre-commit/pre-commit-hooks` (v4.6.0):
- `trailing-whitespace` — removes trailing spaces from every line
- `end-of-file-fixer` — ensures every file ends with exactly one newline
- `check-yaml` — validates YAML syntax (`.pre-commit-config.yaml`, `ci.yml`, etc.)
- `check-toml` — validates TOML syntax (`pyproject.toml`)
- `check-merge-conflict` — rejects commits containing `<<<<<<< HEAD` conflict markers
- `debug-statements` — rejects commits containing `breakpoint()` or `pdb.set_trace()`
- `check-added-large-files` (500 KB limit) — prevents accidentally committing model
  weights, datasets, or large binary files

---

### `.flake8`

Flake8 does not read `pyproject.toml` — this is a known long-standing limitation.
The `.flake8` file provides the configuration `pyproject.toml` cannot.

`max-line-length = 88` — Matches black's line length. Without this, flake8 flags lines
black produces as valid (black allows up to 88 characters; flake8's default is 79).

`extend-ignore = E203, W503` — Two rules that conflict specifically with black's output:
- E203: "whitespace before ':'" — black intentionally puts spaces before colons in slice
  notation (`x[1 : 2]`), which flake8 calls a violation.
- W503: "line break before binary operator" — black breaks long lines before operators,
  which is PEP 8-recommended since 2016 but not yet flake8's default.

`exclude` — Tells flake8 to ignore `.git`, `.venv`, `__pycache__`, and the build
directories inside `agenteval/` so it does not lint generated or dependency code.

---

## 4. The Future Roadmap

### Phase 1 — Build the Target (Weeks 1-3)

Phase 1 is about building a working system before adding any security. The temptation to
add validation or guards while building the tools must be actively resisted. If you guard
the system before you can attack it, you will never know whether your guard actually works.

#### Week 1 — Setup and Scaffolding

The `tests/conftest.py` Ollama pre-warm fixture needs its actual implementation: a
function that sends an HTTP POST to `http://localhost:11434/api/generate` with a minimal
prompt and asserts a 200 response. This verifies Ollama is running and the model is
loaded before any slow LLM-dependent test begins.

Confirm `scripts/seed_fixtures.py` produces consistent data across clean checkouts on a
fresh machine by doing a literal `git clone` test and following the Quick Start
instructions in README.md end-to-end.

Verify the GitHub Actions CI pipeline passes end-to-end by making a small code change
and watching both the lint and test jobs pass.

Finalise the mock data design: confirm the customer record schema, wiki topic structure,
and message log format match what the Week 2 tools will need to read and write.

#### Week 2 — The Target: MCP Server

`reference_system/mcp_server.py` is implemented with three tools using the official MCP
Python SDK.

`query_customer_db(customer_id: str) -> dict` reads from `fixtures/customers.db` and
returns name, email, balance, and tier. Validates that `customer_id` is a non-empty
alphanumeric string before querying. Pydantic schema defined here. No other security
validation — the middleware's job.

`read_internal_wiki(topic: str) -> str` looks for a corresponding `.txt` file in
`fixtures/wiki/` and returns its contents. Topics map to filenames (topic `"billing"`
maps to `billing.txt`). Returns a structured "not found" response if the file does not
exist — the agent needs to handle missing topics gracefully without exceptions.

`send_slack_message(channel: str, text: str) -> dict` appends a JSON-formatted log entry
to `fixtures/messages.log` with timestamp, channel, and text. Does not send to a real
Slack workspace. The log file is the evidence trail: after an attack run, read it to see
whether sensitive data was exfiltrated.

Each tool has a Pydantic input model for two reasons: the MCP SDK needs the schema to
describe the tool to the agent, and it provides a first line of type validation even in
the undefended system.

Week 2 acceptance criterion: manual smoke test — call each tool directly (not through the
agent) and confirm it returns realistic-looking output.

#### Week 3 — The Brain: LangGraph Orchestrator

`reference_system/agent.py` is implemented as a LangGraph graph with at minimum two node
types: a reasoning node (calls the LLM with current state, determines next action) and a
tool execution node (calls the selected tool through the MCP client, updates state).
Routing is conditional: after reasoning, if a tool was chosen, route to tool execution;
if the agent chose to respond, route to output.

The agent must handle multi-step requests. Example: "Look up customer 4471 and send them
their balance" requires: (1) call `query_customer_db("4471")`, observe balance = $1420.50,
(2) call `send_slack_message` with the customer's contact info and balance, (3) respond
confirming it was done. LangGraph's state management handles this across steps.

OpenTelemetry spans are hooked into LangGraph's callback system so every LLM call and
every tool call produces a span in the trace. These spans are written to `traces.db` via
`trace_processor.py`.

Week 3 acceptance criterion: manual run of 5-10 varied prompts confirming the agent
behaves sensibly. Do not start Phase 2 until Phase 1 works correctly — an attack that
gets through a broken system proves nothing.

---

### Phase 2 — Attack and Defend (Weeks 4-5)

Phase 2 is the core of the security story. Week 4 breaks the system; Week 5 fixes it.
The before/after evidence is the credibility of the entire project.

#### Week 4 — Red Team

All three attack scripts in `attacks/` are implemented and run against the undefended
Week 3 agent.

**SAFE-T1201 (Prompt Injection — Tool Hijack):** Embeds adversarial instructions in a
field the agent reads — for example, in the user message text, or injected into wiki
content the agent retrieves. The injection instructs the agent to call a different tool
than intended or with arguments that were not specified. A successful attack: the agent
makes a tool call it was not asked to make. The script captures the tool call log and
verifies the injection succeeded before Week 5 begins.

**SAFE-T1203 (Tool Argument Hijacking):** Sends deliberately malformed arguments —
extremely long strings, special characters, SQL injection patterns, arguments exceeding
Pydantic schema constraints. Against the undefended system, some may bypass the tool's
basic type checks and cause unexpected behavior. The script tests a battery of malformed
inputs and records which ones the undefended system accepts.

**SAFE-T1208 (Indirect Data Exfiltration):** Manipulates the agent into a two-step
exfiltration: retrieve sensitive customer data via `query_customer_db`, then forward it
through `send_slack_message` to an attacker channel. The attack does not say "leak data"
— it frames the request so the agent believes it is doing something legitimate. Success:
the balance and email appear in `messages.log`.

Each script documents what it did and what the result was. This becomes the "before"
section of the final results comparison.

#### Week 5 — The Shield: Guardrail Middleware

`reference_system/middleware.py` is fully implemented with four layers:

**Input validation layer:** Every tool call passes through a Pydantic validator before
reaching the MCP server. Schemas are stricter than the tool's own: `customer_id` must
match `^[0-9]{4}$` (exactly four digits). An argument like `4471; DROP TABLE customers`
fails and is rejected before reaching SQLite.

**Permission scoping layer:** Each tool call is checked against a defined permission scope
for the current conversation context. The agent does not have blanket access to all tools
in all contexts. If the current scope is "read-only customer lookup," a call to
`send_slack_message` is rejected regardless of whether its arguments are well-formed.
This stops privilege creep across multi-step conversations — the mechanism SAFE-T1201
exploits.

**Output filtering layer:** Before the result of any tool call is passed to the next
step, it is scanned for sensitive data patterns: account balances (numeric patterns
matching financial amounts), email addresses (RFC 5322 pattern), anything that looks
like a credential or token. When `send_slack_message` is called with text containing any
of these patterns, the middleware blocks the call, logs a structured event, and returns
a rejection to the agent.

**Structured logging:** Every block emits a JSON log entry with: the SAFE-MCP technique
ID being blocked (if known), the tool name, the timestamp, the decision (BLOCKED), and
the reason (which rule triggered). This log is what AgentEval reads in Phase 3 to score
the run.

After Week 5, all three Week 4 attacks are re-run against the defended system. Expected
result: all three blocked. If any get through, the middleware is incomplete.

---

### Phase 3 — Measure and Package (Weeks 6-8)

Phase 3 turns Phases 1 and 2 into reproducible, comparable evidence.

#### Week 6 — The Ruler: AgentEval Harness

All four skeleton files in `agenteval/agenteval/` are fully implemented.

`storage.py` implements `TraceStore` wrapping `traces.db`. Creates schema on first use
(a `spans` table: run_id, span_id, parent_span_id, name, start_time, end_time,
attributes). Provides `write_span()` and `query_spans()`. All queries go through this
class — no other module writes raw SQL against `traces.db`.

`telemetry/trace_processor.py` subscribes to the OTel span export pipeline, receives
`ReadableSpan` objects, extracts `gen_ai.*` attributes (model name, token counts, tool
name, arguments, result), and writes flat rows to `TraceStore`. Flattens at ingestion —
a LangGraph run produces a tree of spans; flat rows make scoring queries simple fast
joins instead of recursive tree traversals.

`metrics/task_success.py` implements `score_task(store, run_id, expected_tools)`. Queries
spans for a given run, checks expected tools were called in reasonable order, computes
token efficiency, returns a structured result.

`metrics/security.py` implements `score_security_run(store, run_id, technique_id)`. Reads
the middleware's block log, checks whether the block event for the given technique ID was
emitted, returns BLOCKED, PASSED, or PARTIAL.

`plugin.py` implements the pytest plugin. The `--agenteval` flag enables it. When
enabled, registers session-level fixtures that start a `TraceStore` session, pass the
store to each security test via fixture, and generate a summary report at session end:
which techniques were blocked, which passed, aggregate score.

`tests/test_security.py` is updated from skipped stubs to parametrized tests that
actually run each attack script and assert the AgentEval scoring result.

Week 6 acceptance criterion: `pytest tests/test_security.py --agenteval -v` produces a
report showing BLOCKED for all three implemented techniques.

#### Week 7 — Benchmarking Across Models

At least two comparison points are benchmarked:

- Full-precision model: e.g., `llama3.2:8b` (default Ollama download)
- Quantized variant: e.g., `llama3.2:8b-q4_K_M` (4-bit quantized)

For each model, the full AgentEval suite runs: three task correctness scenarios from
`test_agent_behavior.py` and three attack scenarios from `test_security.py`. Results
recorded in structured CSV/JSON.

Questions being answered: Does quantization change task success rate? Does it change how
often the guardrail needs to act (does the quantized model attempt more suspicious tool
calls that the middleware has to block)? Does the model's behavior under adversarial
prompting change at different precision levels?

If time allows, a third data point (8-bit quantization) produces a trend rather than two
dots. This is explicitly optional — only pursue if Weeks 1-6 finished on schedule.

#### Week 8 — Packaging

`Dockerfile` and `docker-compose.yml` containerise `reference_system/`. Ollama stays on
the host. Compose file sets `OLLAMA_BASE_URL=http://host.docker.internal:11434` and
`extra_hosts: ["host.docker.internal:host-gateway"]` for Linux CI compatibility.

`docs/THREAT_MODEL.md` updated to reflect the actual system — every technique that was
actually blocked gets status updated to "Blocked (with test)" with a link to the specific
test proving it.

PyPI name verified: `pip install mcp-guardeval` must fail with "No matching distribution
found" immediately before publishing. If taken, fallback to `mcp-guardeval-py` or
`mcp-guard-eval`.

`poetry build` and `poetry publish` run from inside `agenteval/` to publish
`mcp-guardeval` to PyPI.

Root `README.md` rewritten for a reader with two minutes: leads with what the agent does
and why it is interesting (not an installation wall), includes a terminal recording or
screenshot showing an attack being blocked, links to the published library, includes
actual benchmark numbers from Week 7.

Final clean-checkout test: `git clone && <setup command>` on a machine that has never had
the repo before. If that does not work within five minutes, something in the documentation
is wrong. Fix it before calling Week 8 done.

---

## Appendix: Quick Reference

| Component | Location | Status | Week |
|---|---|---|---|
| Planning docs (PROJECT, ARCHITECTURE, ROADMAP, CONVENTIONS) | `docs/` | Done | 0 |
| Threat model | `docs/THREAT_MODEL.md` | Done (living doc) | 0 |
| `.gitignore` | `.gitignore` | Done | 0 |
| Root `pyproject.toml` | `pyproject.toml` | Done | 0 |
| Pre-commit hooks | `.pre-commit-config.yaml` | Done | 0 |
| `.flake8` config | `.flake8` | Done | 0 |
| GitHub Actions CI | `.github/workflows/ci.yml` | Done | 0 |
| Seed fixtures script | `scripts/seed_fixtures.py` | Done | 0 |
| Mock customer data + wiki | `reference_system/fixtures/` | Done | 0 |
| Test skeletons | `tests/` | Scaffolded | 0 |
| AgentEval skeletons | `agenteval/agenteval/` | Scaffolded | 0 |
| Attack skeletons | `attacks/` | Scaffolded | 0 |
| Ollama pre-warm fixture | `tests/conftest.py` | TODO | 1 |
| MCP server (3 tools) | `reference_system/mcp_server.py` | TODO | 2 |
| LangGraph agent | `reference_system/agent.py` | TODO | 3 |
| OTel tracing | `reference_system/agent.py` | TODO | 3 |
| Attack scripts (3 techniques) | `attacks/` | TODO | 4 |
| Guardrail middleware | `reference_system/middleware.py` | TODO | 5 |
| AgentEval full implementation | `agenteval/agenteval/` | TODO | 6 |
| Cross-model benchmarking | — | TODO | 7 |
| Docker packaging | `Dockerfile`, `docker-compose.yml` | TODO | 8 |
| PyPI publish (`mcp-guardeval`) | `agenteval/` | TODO | 8 |
| Final README | `README.md` | TODO | 8 |
