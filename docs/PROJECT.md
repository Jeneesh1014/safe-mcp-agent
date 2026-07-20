# Safe-MCP-Agent

A local-first system that shows the full lifecycle of securing an AI agent: build an
agent that can call tools, attack it, defend it, and then prove — with numbers, not
vibes — how well the defense actually works.

This file is the entry point. Read this first before touching any code.

## Repo and package identity

- **GitHub repo:** `safe-mcp-agent` — public, MIT licensed, this is the whole project.
- **This is an application-first project.** The secured agent is the product. The
  README leads with the agent and its security story, not with the library.
- **The library is real, not a side note.** `agenteval/` inside this repo is a
  genuinely standalone, independently installable evaluation package. It gets
  published to PyPI as `mcp-guardeval` (name confirmed available — double-check
  with `pip install mcp-guardeval` right before actually publishing, since search
  results can lag the live registry).
- So there are two products living in one repo: the application (not published
  separately, lives only here) and the library (published, usable by anyone outside
  this project). See `ARCHITECTURE.md` for exactly how that split is structured.

## Why this project exists

Most student "AI agent" projects are a chatbot wrapped around an API call. That's not
what companies are hiring for anymore. Job postings for AI Engineer roles in Germany
right now ask for the same handful of things over and over: people who can build
multi-agent orchestration (LangGraph, CrewAI), deploy it properly (Docker, APIs,
observability), and — increasingly — people who understand agent security, because
nobody has solved it yet and every company running agents in production is worried
about it.

MCP (Model Context Protocol) is the part of this that's moving fastest. It's how
agents connect to tools and data now — Anthropic handed it over to a Linux Foundation
project at the end of 2025, and adoption has been steep enough that it's already
showing up as a named skill in job listings. Almost nobody applying for junior/new-grad
roles has actually built an MCP server, let alone attacked or defended one. That gap is
the whole point of this project.

So instead of building "an agent," we're building four things that fit together:

1. **A target** — a small MCP server with tools an agent can call: customer lookup,
   a compiled knowledge-base query (via OpenKB — see below), and sending a
   Slack-style message. Deliberately built with no security at first.
2. **A brain** — a LangGraph agent that decides which tools to call and in what order
   to accomplish a task.
3. **A shield** — a guardrail layer sitting between the agent and the MCP server that
   validates inputs, scopes permissions, and blocks known attack patterns before they
   reach a tool.
4. **A ruler** — an evaluation harness (AgentEval) that automatically attacks the agent
   using real, catalogued attack techniques and measures how often the shield actually
   stops them, across different models and quantization levels.

The end state isn't a demo you click through once. It's a `pytest` suite you can run
that spits out a report: which attacks got through, which got blocked, and how that
changes when you swap the model underneath.

## The knowledge base: OpenKB, not a flat text reader

The original plan had `read_internal_wiki` just reading plain text files — fine for a
first pass, but it made the "target" the least impressive part of the system and gave
the guardrail layer nothing realistic to defend. We're replacing it with
[OpenKB](https://github.com/VectifyAI/OpenKB), a real, actively maintained open-source
tool that compiles raw documents (PDFs, Word, Markdown, etc.) into a structured,
cross-referenced wiki using an LLM, backed by PageIndex's tree-based retrieval instead
of vector chunking.

Why this is worth the extra dependency:

- It gives the agent something genuinely non-trivial to query — a compiled knowledge
  base with summaries, concept pages, and cross-references, not a keyword search over
  flat files.
- It gives the guardrail layer a much more realistic thing to defend. Content sitting
  inside compiled documents is a real attack surface (indirect prompt injection via
  retrieved content, not just the user's direct message) — a genuinely harder and more
  enterprise-relevant problem than a single vulnerable database field.
- It's local-first compatible: OpenKB supports local models through LiteLLM
  (including Ollama), so it fits the zero-API-cost constraint for day-to-day use.

Two things to keep honest about this dependency, so it doesn't quietly eat the
timeline:

- **The compile step happens once, up front**, not repeatedly during development.
  Treat it as Week 1 prep: compile the mock documents early, then just query the
  result for the rest of the build.
- **Everything runs local, including the compile step — no exceptions, $0 cost.**
  OpenKB uses LiteLLM under the hood, which natively supports routing to a local
  Ollama model (e.g. `ollama/llama3` or `ollama/qwen2.5`) instead of a hosted API.
  Configure `.openkb/config.yaml` to point at the local Ollama endpoint before
  running the first compile. Compilation may take longer on an M1 Pro than it
  would against a hosted frontier model, and the resulting wiki may be a bit
  rougher — that's an accepted tradeoff, not a problem to solve by reaching for a
  paid key. If a specific document consistently produces a bad compile, the fix is
  a better local model or a simpler mock document, not an API call.
- **OpenKB's "Skill Factory" feature is not a committed deliverable.** It looks
  genuinely useful (auto-generating agent skills from the compiled wiki) but is
  newer and less proven than the core compile/query functionality. Treat it as a
  stretch goal — nice if time allows in Week 8, not something the roadmap depends on.
- The original flat-text `read_internal_wiki` tool stays in as a fallback. It costs
  almost nothing to keep and gives Week 7's benchmarking an extra angle: naive
  retrieval vs. tree-based retrieval, on top of the model/quantization comparison
  already planned.

## What "done" looks like

- A working MCP server exposing 3 tools (customer lookup, OpenKB-backed wiki query,
  plus the flat-text fallback reader, and message sending), running locally.
- A LangGraph agent that can chain those tools to complete multi-step requests.
- A guardrail middleware that intercepts every tool call, checks it against a defined
  threat model, and logs what it blocks (not just silently drops it).
- An automated attack suite built against real SAFE-MCP technique IDs (not made-up
  test cases) — this is the part that makes the security story credible instead of
  hand-wavy.
- A benchmark comparing at least two models (e.g. a full-precision model vs. a
  quantized one) on both task success and how easily each one gets exploited.
- The whole thing containerized, with a README someone can read in two minutes and
  understand exactly what it does and why it's interesting.
- No dependency on a paid API. Everything runs locally through Ollama. That's a
  deliberate constraint — it means anyone can clone the repo and actually run it,
  which matters a lot more for an open-source portfolio piece than people assume.

## What this project is explicitly not trying to be

- Not a general-purpose chatbot. The agent has a narrow, fixed job (look things up,
  send a message) — the interesting part is the security layer around it, not the
  breadth of what it can do.
- Not a research paper on novel attack discovery. We're implementing and measuring
  against an existing, respected framework (SAFE-MCP), not inventing new attack
  classes. That's a feature, not a limitation — it means the results are comparable
  and credible.
- Not dependent on cloud infrastructure. Local dev on a MacBook M1 Pro, Ollama for
  inference, SQLite for storage. If a step needs a paid service, that's a sign we've
  gone off track.

## High-level plan

Roughly two months, structured in three phases. See `ROADMAP.md` for the actual
week-by-week breakdown with checkboxes.

**Phase 1 — build the target.** Get the MCP server and the LangGraph agent working
together with zero security. The agent should be able to take a plain-English request
and correctly chain 2-3 tool calls to satisfy it. No guardrails yet — the doors are
deliberately left open here.

**Phase 2 — break it, then fix it.** Red-team the open system using real SAFE-MCP
technique IDs. Once we know exactly how it breaks, build the guardrail middleware to
stop those specific attacks, and make sure every block gets logged, not swallowed.

**Phase 3 — measure it and package it.** Build the evaluation harness that automates
the attacks from Phase 2 and turns them into a repeatable benchmark. Run it against
more than one model/quantization level to get an actual comparison, not a single data
point. Then containerize everything and write the documentation.

## Before Week 1 starts

This isn't part of the coding roadmap — it's the setup that needs to exist before any
of it:

- GitHub repo created (`safe-mcp-agent`, public, MIT license, description and topics
  set — see `ROADMAP.md` "Week 0" for the exact steps)
- Ollama installed locally, one model pulled, confirmed responding on
  `localhost:11434`
- Poetry installed
- Docker Desktop installed and confirmed running (not used until Week 8, but worth
  knowing it works now)
- The four planning docs (this one, `ARCHITECTURE.md`, `ROADMAP.md`,
  `CONVENTIONS.md`) committed to the repo before any feature code

## Where the pieces live

See `ARCHITECTURE.md` for the actual directory layout and how the pieces talk to each
other. See `CONVENTIONS.md` before writing any code — it covers commit style, comment
style, and a few things to avoid so the codebase reads like it was written by one
person who knew what they were doing, not stitched together.

## Constraints that shape every decision here

- **Hardware:** MacBook M1 Pro. Ollama runs natively on the host for GPU access
  (Metal) — it does not run inside Docker. Anything containerized talks to it over
  `host.docker.internal`.
- **Cost: $0.00, no exceptions.** No OpenAI/Anthropic API keys anywhere in this
  project, including one-off or setup-only steps. Every LLM call — agent
  reasoning, guardrail decisions, and OpenKB's document compilation — runs through
  local Ollama models. If a step is tempting to solve with a hosted API call
  because a local model struggles, the answer is a better local model, a smaller
  prompt, or a simpler mock document — not a paid key. This is a hard constraint,
  not a default that bends under time pressure.
- **Reproducibility:** Anyone should be able to `git clone`, run one setup command,
  and have the whole thing running locally within a few minutes.
