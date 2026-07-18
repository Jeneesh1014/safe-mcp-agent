# Safe MCP Agent

A local LLM agent (LangGraph + MCP) with a red-teamed guardrail layer and an automated
evaluation harness that benchmarks security and task performance across models.

> 🚧 Work in progress — Week 0 scaffolding complete, implementation starting.

## What this is

Four things that fit together:

| Layer | What it does |
|---|---|
| **MCP server** | Exposes 3 mock enterprise tools an agent can call |
| **LangGraph agent** | Decides which tools to call and in what order |
| **Guardrail middleware** | Intercepts every tool call, validates it against a threat model, logs what it blocks |
| **AgentEval harness** | Automatically attacks the agent using real SAFE-MCP technique IDs and measures how often the shield stops them |

The end state is a `pytest` suite you can run that produces a report: which attacks
got through, which got blocked, and how that changes when you swap the underlying model.

## Quick start

> **Prerequisites:** [Ollama](https://ollama.com) installed and running, [Poetry](https://python-poetry.org) installed.

```bash
git clone https://github.com/<your-username>/safe-mcp-agent.git
cd safe-mcp-agent
poetry install
ollama pull llama3.2          # or whichever model you prefer
python scripts/seed_fixtures.py
pytest tests/ -m "not slow"
```

## Running the agent

```bash
poetry run python -m reference_system.agent
```

## Running the security suite

```bash
pytest tests/test_security.py --agenteval -v
```

## Project structure

```
safe-mcp-agent/
├── reference_system/   the agent under test (MCP server + LangGraph + guardrail)
├── agenteval/          evaluation library — published separately as mcp-guardeval
├── attacks/            red-team scripts, one file per SAFE-MCP technique
├── tests/              pytest suite (behavior + security)
├── scripts/            setup helpers (seed_fixtures.py, etc.)
├── dashboard/          optional Next.js trace viewer
└── docs/               planning documents
```

See [`docs/PROJECT.md`](docs/PROJECT.md) for the full project rationale,
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for system design,
and [`docs/ROADMAP.md`](docs/ROADMAP.md) for the week-by-week plan.

## Hardware constraint

Ollama runs **natively on the host** (not in Docker) to access the Mac GPU via Metal.
Containers reach it at `http://host.docker.internal:11434`.

## License

MIT — see [`LICENSE`](LICENSE).
