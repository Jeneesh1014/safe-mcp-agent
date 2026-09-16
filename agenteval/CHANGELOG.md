# Changelog

All notable changes to **mcp-guardeval** are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [0.3.2] — 2026-09-16

### Changed
- Replaced Mermaid diagram in README with static image link for PyPI compatibility.

## [0.3.1] — 2026-09-16

### Changed
- README rewrite: removed promotional puffery, emoji bullets, and AI writing patterns.
- Clearer configuration and CLI documentation.

## [0.3.0] — 2026-09-16

### Added
- **CLI entrypoint** — `python -m agenteval` (or `guardeval` after install) prints
  the same summary report as the pytest plugin, without requiring a test suite.
- **Public API re-exports** — `from agenteval import TraceStore, score_task,
  score_security_run` now works. Deep imports still supported.
- **`__version__`** — `agenteval.__version__` available at runtime.
- **Architecture diagram** in README (Mermaid).
- **"How It Works"** section explaining deterministic scoring philosophy.
- **Comparison table** positioning against MCPEval, DeepEval, and Promptfoo.
- **Contributing** section in README.
- This **CHANGELOG.md**.
- PyPI classifiers: `Framework :: Pytest`, `Topic :: Security`.

## [0.2.0] — 2026-09-10

### Added
- **Configurable pytest plugin** — `guardeval_techniques`, `guardeval_log`,
  `guardeval_traces_db`, `guardeval_block_threshold` all settable via
  `pyproject.toml` `[tool.pytest.ini_options]`.
- **Technique auto-discovery** from guardrail logs when no explicit list
  is configured (`discover_techniques()`).
- **`summary()` convenience methods** on `TaskResult` and `SecurityResult`.
- Professional README written for external PyPI adopters.

### Changed
- `score_security_run` now also checks `tool.result_redacted` and
  `tool.result_redaction_technique` span attributes for redaction-based blocks.

### Fixed
- `PARTIAL` verdicts now only assigned when tool errors are directly tied
  to the specific technique, preventing unrelated errors from degrading
  the block rate.

## [0.1.0] — 2026-08-28

### Added
- Initial release as `mcp-guardeval` on PyPI.
- `TraceStore` — read-only SQLite interface to OpenTelemetry traces.
- `load_guardrail_log` / `discover_techniques` — JSONL log parsing.
- `score_task` — deterministic task success scoring (tool coverage,
  argument correctness, error absence, completion).
- `score_security_run` — per-technique BLOCKED / PASSED / PARTIAL verdicts.
- `extract_tool_calls` / `extract_llm_calls` / `extract_run_summary` —
  span normalization into typed Pydantic records.
- `pytest --agenteval` plugin with terminal summary report.
- `py.typed` marker for PEP 561 compliance.
