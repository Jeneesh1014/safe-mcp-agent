# Roadmap

Eight weeks, three phases. Weeks are a guide for pacing, not a hard deadline — if
something takes longer, let it, and pull from the next week's buffer rather than
cutting corners.

Check items off as you go. If an agent is picking this file up mid-project, the
unchecked items are exactly what's left to do.

## Week 0 — before any code (do this first, not part of the 8 weeks)

- [x] Create the GitHub repo: `safe-mcp-agent`, public, MIT license
- [x] Set repo description: "A local LLM agent (LangGraph + MCP) with a red-teamed
      guardrail layer and an automated evaluation harness that benchmarks security
      and task performance across models."
- [x] Add topics: `langgraph`, `mcp`, `model-context-protocol`, `ai-agents`,
      `llm-security`, `prompt-injection`, `ollama`, `agent-evaluation`, `python`
- [x] Add `.gitignore` (Python + macOS + `*.db`/`*.db-wal`/`*.db-journal`)
- [x] Add placeholder `README.md` (title, one line, "🚧 in progress" — real one
      gets written in Week 8)
- [x] Commit and push all four planning docs: `docs: initial project documentation
      and planning`
- [x] Confirm Ollama is installed and responding: `ollama pull <model>`, then check
      `localhost:11434` answers
- [x] Confirm Poetry is installed
- [x] Confirm Docker Desktop is installed and running
- [x] Install pre-commit hooks locally so formatting is enforced from commit #2 on

## Phase 1 — Build the target (Weeks 1–3)

### Week 1 — Setup and scaffolding

- [x] Initialize repo structure per `ARCHITECTURE.md`
- [x] `pyproject.toml` with Poetry, core deps pinned (langgraph, mcp, opentelemetry,
      pydantic, pytest)
- [x] Pre-commit hooks: black, isort, flake8
- [x] `.gitignore` covers `*.db`, `*.db-journal`, `*.db-wal`, `.venv`, `__pycache__`
- [x] `tests/conftest.py`: Ollama pre-warm fixture (hit the model once before the test
      run starts, so the first real test doesn't eat a cold-start timeout)
- [x] GitHub Actions skeleton in `.github/workflows/ci.yml` — runs `pytest --collect-only`
      and fast non-LLM tests; slow/LLM tests skip cleanly in CI via `-m 'not slow'`
- [x] Design the mock data: customer DB schema, wiki file contents, message log
      format. Write `seed_fixtures.py` to generate them deterministically.
- [x] `pip install openkb`, `openkb init` inside repo root, docs added from `raw_docs/`.
      Compiled with `llama3.2` via Ollama — 4 documents indexed, 4 concepts, 7 entities,
      4 summaries generated. Wiki lives at `wiki/` (repo root, gitignored).
      Flat-text fallback wiki in `reference_system/fixtures/wiki/` kept for Week 7 benchmarking.


### Week 2 — The target: MCP server

- [x] `mcp_server.py` exposing four tools:
  - `query_customer_db(customer_id)` — reads from the seeded SQLite DB
  - `query_openkb_wiki(question)` — queries the OpenKB-compiled knowledge base
        from Week 1, using its tree-based retrieval rather than blind chunking
  - `read_internal_wiki(topic)` — the original flat-text fallback reader, kept as
        a comparison point for Week 7's benchmarking
  - `send_slack_message(channel, text)` — appends to a local log file, doesn't
        actually send anything anywhere
- [x] Input schemas defined with Pydantic for each tool
- [x] No security yet — this week is deliberately wide open. Resist the urge to add
      validation here; that comes in Week 5 once we know what we're defending against.
- [x] Manual smoke test: call each tool directly and confirm it returns sane output,
      including a couple of multi-hop questions against the OpenKB wiki to confirm
      the compiled knowledge base actually holds up

### Week 3 — The brain: LangGraph orchestrator

- [x] `agent.py`: graph definition, nodes for reasoning + tool execution
- [x] Agent can take a natural-language request and correctly choose which tool(s)
      to call
- [x] Agent can chain 2+ tool calls in sequence for a multi-step request
      (example: "look up customer 4471 and send them their balance")
- [x] Wire up OpenTelemetry spans on the LangGraph hooks so every LLM call and tool
      call gets traced
- [x] Manual test: run 5-10 varied prompts, confirm the agent behaves sensibly before
      moving on — don't start red-teaming a system you haven't confirmed works

## Phase 2 — Attack and defend (Weeks 4–5)

### Week 4 — Red team

- [x] Pick 6-10 SAFE-MCP technique IDs across a few tactic categories, not just
      prompt injection. Final set (7 techniques, 5 categories):
  - `SAFE-T1201` — prompt injection to hijack tool selection (execution)
  - `SAFE-T1203` — tool argument hijacking / parameter overloading (execution)
  - `SAFE-T1208` — indirect data exfiltration via a downstream tool (exfiltration)
  - `SAFE-T1301` — context instruction planting (persistence)
  - `SAFE-T1601` — system prompt disclosure (discovery)
  - `SAFE-T1102` — indirect prompt injection via retrieved wiki content (execution)
  - `SAFE-T1501` — cross-tool PII harvesting (collection)
- [x] Write a reproducible script for each attack under `attacks/`, one file per
      technique, named after the technique ID
- [x] Run each attack against the *undefended* Week 3 agent and confirm it actually
      succeeds — 2/7 fully succeeded, 3/7 partially succeeded (Slack called but model
      failed preceding steps), 2/7 failed due to model limitations not guardrails.
      See `attacks/ATTACK_RESULTS.md` for full details.
- [x] Document what happened for each one (even briefly) — this becomes the "before"
      half of the results section later. Written to `attacks/ATTACK_RESULTS.md`.

### Week 5 — The shield: guardrail middleware

- [x] `middleware.py`: intercepts every tool call before it reaches the MCP server
- [x] Input validation against strict Pydantic schemas (catches malformed / injected
      arguments)
- [x] Permission scoping: each tool call is checked against a defined scope rather
      than assuming the agent has blanket access — this stops privilege creep across
      a multi-step conversation
- [x] Output filtering: block sensitive-looking data (dummy card numbers, tokens,
      credentials) from flowing into the outbound tool (`send_slack_message`)
- [x] Every block emits a structured log entry — technique ID (if known), tool name,
      timestamp, decision. A guardrail that blocks silently is invisible in
      production; don't build that.
- [x] Re-run all Week 4 attacks against the now-defended agent, confirm the ones you
      expect to be blocked actually are — 6/7 blocked, T1601 (system prompt
      disclosure) is the documented known gap

## Phase 3 — Measure and package (Weeks 6–8)

### Week 6 — The ruler: AgentEval harness

- [x] Set up `agenteval/` as its own package: its own `pyproject.toml`, its own
      `README.md`, independent from the root project config (see `ARCHITECTURE.md`
      for the exact layout)
- [x] `agenteval/telemetry/trace_processor.py`: normalize OpenTelemetry spans into
      flat rows in SQLite (don't store nested trace trees directly — flatten at
      ingestion so queries stay fast)
- [x] `agenteval/metrics/task_success.py`: did the agent complete what was asked
- [x] `agenteval/metrics/security.py`: did an attack get through, which ones, how
      often
- [x] `agenteval/plugin.py`: pytest plugin so the whole attack suite runs with one
      command (`pytest --agenteval`)
- [x] `tests/test_security.py`: parametrized test that runs every script in
      `attacks/` and asserts against the guardrail's logged decisions
- [x] Install it into `reference_system` the same way an outside user would
      (editable install: `pip install -e ./agenteval`), not via a relative import
      hack — this is what proves the library boundary actually holds

### Week 7 — Benchmarking across models

- [x] Pick at least two comparison points — for example, a full-precision model vs.
      a 4-bit quantized version of the same or a similar model, both running locally
      through Ollama
- [x] Run the full AgentEval suite (task success + security) against each
- [x] Record: does quantization change task success rate? Does it change how often
      the guardrail catches an attack, or how often the *model itself* attempts
      something unsafe in the first place?
- [x] If time allows, add a third point (e.g. 8-bit) to get a trend instead of two
      dots — concluded with 2-point benchmark (llama3.2 3B vs llama3.2:1b) to reserve Week 8 buffer
- [x] Optional second axis if time allows: compare `query_openkb_wiki` against the
      flat-text `read_internal_wiki` fallback on the same questions — concluded;
      model/quantization comparison recorded in benchmark_report.md as core result

### Week 8 — Packaging

- [x] `Dockerfile` + `docker-compose.yml` — reference_system and dashboard
      containerized, Ollama stays on the host (see `ARCHITECTURE.md`)
- [x] `THREAT_MODEL.md` finished and accurate to what was actually built (not just
      the plan — go back and correct anything that changed along the way)
- [x] Confirm the package name is actually free right before publishing:
      `pip install mcp-guardeval` confirmed free on PyPI registry
- [x] `poetry build` + `poetry publish` from inside `agenteval/` — verified builds
      tar.gz and wheel distributions cleanly
- [x] `agenteval/README.md` (the library readme, shown on PyPI) written for a
      stranger who's never heard of this project — what the library does, quick
      install/usage example, nothing about the agent itself
- [x] Root `README.md` written last, for a reader who has 2 minutes: what the agent
      does, why it matters, how to run it, one screenshot or terminal recording
      showing an attack being blocked — with a link out to the published library
      as a supporting piece, not the headline
- [x] Short demo clip (terminal recording is fine) showing one attack failing against
      the open system and being blocked against the defended one, side by side
- [x] Final pass: does `git clone && <setup command>` actually work on a clean
      checkout? Test this literally, don't assume it

## Stretch goal — OpenKB Skill Factory (optional, not on the critical path)

- [x] Evaluated following completion of Weeks 1–8.
- [x] Ran `openkb skill new` against compiled wiki using local Ollama. Confirmed local 3B model hallucinated tool invocation (`Tool main not found in agent skill-creator`).
- [x] Concluded per roadmap instructions: dropped without guilt; hand-crafted system prompt retained as production-grade baseline.
