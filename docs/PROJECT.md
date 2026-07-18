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

1. **A target** — a small MCP server with tools an agent can call (customer lookup,
   internal wiki search, sending a Slack-style message). Deliberately built with no
   security at first.
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

## What "done" looks like

- A working MCP server exposing 3 mock enterprise tools, running locally.
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
- **Cost:** Zero. No OpenAI/Anthropic API keys required to run the core system.
- **Reproducibility:** Anyone should be able to `git clone`, run one setup command,
  and have the whole thing running locally within a few minutes.
