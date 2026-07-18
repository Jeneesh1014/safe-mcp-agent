# Conventions

Read this before writing or generating any code for this repo. It exists so the
codebase reads like it was written by one person who knew what they were doing over
eight weeks — not stitched together from a dozen disconnected sessions.

## Commit messages

Conventional Commits, no exceptions:

- `feat(scope): ...` — new functionality
- `fix(scope): ...` — bug fix
- `test(scope): ...` — adding or changing tests, no source changes
- `docs(scope): ...` — documentation only
- `refactor(scope): ...` — no behavior change, just cleanup
- `chore(scope): ...` — tooling, deps, config

Scope should match the folder the change lives in: `mcp`, `agent`, `guardrail`,
`telemetry`, `eval`, `attacks`, `ci`, `docs`.

Good: `fix(guardrail): scope permission check per-tool instead of per-session`
Bad: `fix bug`, `updates`, `wip stuff`

If you're stopping mid-feature for the day, commit locally with `wip:` prefix and a
real description of where you left off (`wip: agent routes to wrong tool when two
tools have overlapping keywords`), not just `wip`. Future-you needs the context, not
just the checkpoint.

One functional change per commit. Don't bundle a guardrail fix with an unrelated
formatting pass — makes the history useless for debugging later ("which commit broke
this?" should have one answer).

## Code comments

Comments explain **why**, not what. The code already says what it does — if a
comment just restates the line below it, delete the comment.

Bad:
```python
# increment the counter
counter += 1
```

Good:
```python
# Ollama's cold start on M1 can take 8-10s for the first call; we retry once
# before failing the test so a slow model load doesn't look like a real bug.
if attempt == 0 and error is TimeoutError:
    retry()
```

Only comment the non-obvious parts: a workaround, a constraint from
`ARCHITECTURE.md`, a decision that has a tradeoff someone might question later. If
you're implementing something directly from the threat model or a SAFE-MCP technique,
reference the ID so the connection is traceable:

```python
# SAFE-T1208: block outbound tool calls carrying anything that looks like a
# credential or account token, not just exact string matches on "password".
```

Don't leave comments like `# TODO: fix this later` without a reason or a ticket
reference — either fix it now, or write what "fix" actually means
(`# TODO: this regex misses base64-encoded payloads, needs a decode pass first`).

Docstrings on public functions (anything in `agenteval/` meant to be imported
elsewhere) should say what the function does and what it assumes about its input —
not restate the type hints.

## What to avoid — things that read as generated rather than written

- **No padding phrases.** Don't write "this leverages a robust and scalable
  architecture to seamlessly integrate..." Just say what it does:
  "the guardrail sits between the agent and the MCP server and checks every call."
- **No restating the obvious in variable names or comments** —
  `customer_id_variable_holding_customer_identifier` is worse than `customer_id`.
- **Don't over-engineer for scale you don't have.** This is a portfolio project with
  three tools and a handful of attack scripts, not a system serving production
  traffic. A plugin architecture for "future tool types" that never materializes
  reads as filler, not foresight.
- **Consistent voice.** Pick one style for error messages and stick to it across the
  whole repo — either terse (`"invalid customer_id"`) or descriptive
  (`"customer_id must be alphanumeric, got: {value}"`), not a mix depending on which
  file you're in.
- **No fake precision.** Don't write "achieves 99.7% detection accuracy" unless
  you've actually run the numbers and can show the test that produced them. If the
  real number is "caught 8 out of 10 attack variants in this run," say that.

## Python style

- Type hints on all function signatures in `agenteval/` and `reference_system/` —
  not because it's required by a linter, but because this is the part a stranger
  (or an interviewer) will read first.
- Pydantic models for anything crossing a boundary (tool arguments, MCP responses,
  guardrail decisions) — don't pass around raw dicts between modules.
- `black` + `isort` + `flake8`, enforced via pre-commit. Don't hand-format around
  the linter; if a rule is actively wrong for this project, change the config, don't
  work around it file by file.
- Prefer explicit over clever. If a one-liner needs a comment to explain what it's
  doing, it's probably better as three plain lines.

## Tests

- Test names describe the scenario, not the function: `test_guardrail_blocks_sql_
  injection_in_customer_id`, not `test_middleware_1`.
- Every attack script in `attacks/` needs a corresponding assertion in
  `tests/test_security.py` — an attack that isn't wired into the automated suite
  doesn't count toward the benchmark story.
- Keep fast deterministic checks (schema validation, regex matches) separate from
  slow LLM-dependent checks. Mark the slow ones so `pytest -m "not slow"` gives a
  quick local loop.

## Naming: application vs. library

Two names exist for two different things — don't let them blur together in code,
commits, or docs:

- **`safe-mcp-agent`** — the GitHub repo and the application. Use this when talking
  about the agent, the guardrails, the whole project.
- **`mcp-guardeval`** — the PyPI package name for the library in `agenteval/`. Use
  this in anything library-facing: its own README, PyPI metadata, install
  instructions for someone using it outside this repo.
- **`agenteval`** — the Python import name (`import agenteval`) and the local folder
  name. This can differ from the PyPI name — that's normal (`pip install
  beautifulsoup4` → `import bs4` is the same pattern) — just don't let it cause
  confusion. If someone asks "how do I install this," the answer is `pip install
  mcp-guardeval`, not `pip install agenteval`.

When writing commit messages or comments about the library specifically, prefer
"the library" or `agenteval` (the import name) over the PyPI name — `mcp-guardeval`
only really needs to show up in packaging config, the library's own README, and
publish-related conversation.

## Documentation files

- `THREAT_MODEL.md` gets updated as the actual system changes — if a new tool gets
  added or a mitigation changes, this file needs an edit in the same PR, not a
  follow-up "later" that never comes.
- `README.md` is written for someone who will spend two minutes on it. Lead with
  what the project does and why it's interesting, not with an installation wall of
  text — that goes further down.
