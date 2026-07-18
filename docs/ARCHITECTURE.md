# Architecture

How the pieces fit together, what lives where, and why.

## System overview

```
                        MacBook M1 Pro (host)
                              │
        ┌─────────────────────┴─────────────────────┐
        │                                            │
   reference_system                              agenteval
   (the agent + the shield)                   (the measurement layer)
        │                                            │
   ┌────┴─────┐                                 ┌────┴─────┐
   │ agent.py │ LangGraph orchestrator           │ metrics/ │ scoring logic
   │ mcp_     │ MCP server (the tools)           │ telemetry│ trace capture
   │ server.py│                                  │ plugin.py│ pytest hooks
   │ middle-  │ guardrail interception layer      │ storage. │ SQLite writer
   │ ware.py  │                                  │ py       │
   └────┬─────┘                                 └────┬─────┘
        │                                            │
        └──────────────────┬─────────────────────────┘
                            ▼
                   Ollama (runs on host, not
                   in a container — needs GPU
                   access via Metal)
```

`reference_system` is the thing being tested. `agenteval` is the thing doing the
testing. They're kept in separate top-level folders on purpose — `agenteval` should
never import anything from `reference_system` beyond what it needs to observe (traces,
logs). If `agenteval` starts reaching into the agent's internals to work, that's a sign
the boundary is leaking and it won't work as a general-purpose tool later.

This boundary isn't just tidiness — `agenteval/` is a genuinely separate, independently
installable package. It has its own `pyproject.toml`, gets published to PyPI on its
own as `mcp-guardeval`, and needs to work for someone who has never heard of
`reference_system` at all. `reference_system` consumes it the same way an outside user
would: `pip install` (locally as an editable install during development, from PyPI
once published), then a normal `import agenteval`. This repo is application-first —
the secured agent is the headline product — but the library living inside it has to
stand on its own, not lean on internal shortcuts into the app.

## Request flow, step by step

1. A user (or a test) sends a plain-English request to the LangGraph agent.
2. The agent decides which tool(s) to call and with what arguments.
3. Before any tool call reaches the MCP server, it passes through
   `middleware.py` — the guardrail layer. This checks the arguments against the
   threat model (see `THREAT_MODEL.md`), and either lets it through or blocks it.
4. If blocked, the middleware logs a structured event (technique ID, tool name,
   timestamp) and returns a rejection to the agent instead of executing the tool.
5. If allowed, the call reaches the MCP server, which executes against the mock
   data (SQLite for customer records, flat files for the wiki, an append-only log
   for "sent messages").
6. Every step of this — LLM calls, tool calls, guardrail decisions — gets traced via
   OpenTelemetry and written into `traces.db`.
7. AgentEval reads `traces.db` after a test run and scores it: did the agent complete
   the task, did any attack get through, how many tokens did it burn.

## Directory layout

```
safe-mcp-agent/
├── reference_system/          the agent under test
│   ├── agent.py                LangGraph graph: nodes, edges, routing logic
│   ├── mcp_server.py            the MCP server and its three tools
│   ├── middleware.py            guardrail interception layer
│   └── fixtures/                mock data: sqlite db, wiki text files, message log
│
├── agenteval/                  the evaluation library — published separately as
│   │                           `mcp-guardeval` on PyPI, usable outside this repo
│   ├── pyproject.toml           its own package config, independent of the root one
│   ├── README.md                library-specific readme — what PyPI actually shows
│   ├── agenteval/                the importable package (`import agenteval`)
│   │   ├── telemetry/
│   │   │   └── trace_processor.py   normalizes OpenTelemetry spans into flat rows
│   │   ├── metrics/
│   │   │   ├── task_success.py      did the agent do what was asked
│   │   │   └── security.py          did an attack get through
│   │   ├── plugin.py                pytest plugin — what `--agenteval` hooks into
│   │   └── storage.py               SQLite read/write layer
│
├── attacks/                     red-team scripts, one file per SAFE-MCP technique
│   ├── safe_t1201_prompt_injection.py
│   ├── safe_t1203_tool_hijack.py
│   └── safe_t1208_exfiltration.py
│
├── tests/
│   ├── conftest.py               shared fixtures, Ollama pre-warm hook
│   ├── test_agent_behavior.py    does the agent do the task correctly
│   └── test_security.py          runs the attacks/, asserts guardrail catches them
│
├── dashboard/                    optional Next.js viewer for the traces db
│
├── .github/workflows/
│   └── ci.yml
│
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
├── PROJECT.md
├── ARCHITECTURE.md               (this file)
├── ROADMAP.md
├── CONVENTIONS.md
├── THREAT_MODEL.md
└── README.md                     public-facing summary, written last
```

A rule worth keeping: if a file in `reference_system/` starts importing from
`agenteval/`, or vice versa beyond the trace/log interface, stop and rethink the
boundary. They're two separate concerns that happen to live in the same repo.

## Tech stack and why each piece was picked

| Layer | Tool | Why this one |
|---|---|---|
| Local inference | Ollama | Runs natively on Apple Silicon with GPU access, no API cost, no network dependency |
| Agent framework | LangGraph | Cyclical/stateful orchestration — the thing companies are actually asking for by name |
| Tool protocol | MCP (official Python SDK) | The thing this whole project is about; also now genuinely standard, not a bet |
| Tracing | OpenTelemetry (`gen_ai.*` semantic conventions) | Using the real standard instead of a homemade JSON format means the traces are meaningful to anyone who's seen OTel before |
| Storage | SQLite | Zero setup, fine for local dev, easy to inspect by hand when debugging |
| Test/eval runner | pytest + custom plugin | Keeps the security suite runnable the same way as normal unit tests — one command, one report |
| Containerization | Docker Compose | Standard packaging story; Ollama stays outside the container for GPU reasons (see below) |

## The Ollama / Docker constraint

Docker Desktop on macOS runs inside a Linux VM with no passthrough to the Mac's GPU.
If Ollama runs inside a container, it falls back to CPU and gets slow enough to make
iteration painful. So:

- Ollama runs **natively on the host**, listening on `localhost:11434`.
- Anything inside a container reaches it via `OLLAMA_BASE_URL=http://host.docker.internal:11434`.
- `docker-compose.yml` sets `extra_hosts: ["host.docker.internal:host-gateway"]` so this
  resolves correctly on Linux CI runners too, not just macOS.

This isn't a workaround to apologize for in the README — it's a normal, documented
pattern for local-inference development and worth stating plainly as a design
decision.

## Data model notes

- `traces.db` and any other SQLite files are gitignored. They're runtime state, not
  source. Ship a small `seed_fixtures.py` script instead so anyone can regenerate a
  consistent starting dataset.
- Mock customer data, wiki content, and message logs live under
  `reference_system/fixtures/` as plain text/SQLite, checked into git, so the repo is
  self-contained and runnable without any manual data setup.
