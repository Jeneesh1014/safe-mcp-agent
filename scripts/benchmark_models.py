"""
Benchmark runner — runs the full AgentEval suite against multiple Ollama models.

Core Week 7 deliverable. For each model specified on the command line:
  1. Warms up the model via Ollama's API
  2. Runs every task prompt and scores with agenteval task_success
  3. Runs every attack prompt and scores with agenteval security
  4. Records latency, model name, and all per-run details

Results are written to benchmark_results.json for the report generator.

Usage:
    python scripts/benchmark_models.py llama3.2 llama3.2:1b
    python scripts/benchmark_models.py llama3.2 llama3.2:1b qwen2.5:3b

Requires: Ollama running locally with the specified models already pulled.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Ensure repo root is on path
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from scripts.benchmark_prompts import (  # noqa: E402
    ALL_TECHNIQUE_IDS,
    ATTACK_PROMPTS,
    TASK_PROMPTS,
)

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
RUNS_PER_PROMPT = 3
_BENCHMARK_DIR = _REPO_ROOT / "benchmark_output"


def _warmup_model(model: str) -> bool:
    """Hit Ollama once to load the model into memory. Returns True if reachable."""
    payload = json.dumps({"model": model, "prompt": "hi", "stream": False}).encode()
    req = urllib.request.Request(
        f"{OLLAMA_BASE_URL}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return resp.status == 200
    except (urllib.error.URLError, OSError) as exc:
        print(f"  ✗ Warmup failed for {model}: {exc}")
        return False


def _run_single_task(prompt_entry: dict, run_idx: int) -> dict:
    """Run one task prompt through the agent and collect trace spans."""
    # Import here so env patches take effect
    import reference_system.agent as agent_mod

    traces_db = Path(agent_mod._TRACES_DB)

    # Record which spans existed before this run
    span_count_before = 0
    if traces_db.exists():
        import sqlite3

        conn = sqlite3.connect(str(traces_db))
        span_count_before = conn.execute("SELECT COUNT(*) FROM spans").fetchone()[0]
        conn.close()

    start = time.monotonic()
    try:
        reply = agent_mod.run(prompt_entry["prompt"])
        error = None
    except Exception as exc:  # noqa: BLE001
        reply = ""
        error = f"{type(exc).__name__}: {exc}"
    elapsed_ms = (time.monotonic() - start) * 1000

    # Collect new spans from this run
    spans = []
    if traces_db.exists():
        import sqlite3

        conn = sqlite3.connect(str(traces_db))
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM spans ORDER BY start_ns").fetchall()
        conn.close()
        for row in rows:
            d = dict(row)
            if "attributes" in d and isinstance(d["attributes"], str):
                d["attributes"] = json.loads(d["attributes"])
            spans.append(d)
        # Only keep spans from this run (new ones)
        spans = spans[span_count_before:]

    # Score task success
    from agenteval.metrics.task_success import score_task

    result = score_task(
        spans,
        expected_tools=prompt_entry["expected_tools"],
        expected_args=prompt_entry.get("expected_args"),
    )

    # Extract LLM latencies from spans
    llm_latencies = []
    for s in spans:
        attrs = s.get("attributes", {})
        if s.get("name") == "llm.reason":
            try:
                llm_latencies.append(float(attrs.get("llm.latency_ms", 0)))
            except (ValueError, TypeError):
                pass

    return {
        "prompt_name": prompt_entry["name"],
        "run_index": run_idx,
        "passed": result.passed,
        "score": result.score,
        "details": result.details,
        "reply_snippet": reply[:200] if reply else "",
        "error": error,
        "total_ms": round(elapsed_ms, 1),
        "llm_latencies_ms": llm_latencies,
    }


def _run_single_attack(attack_entry: dict, guardrail_log: Path, run_idx: int) -> dict:
    """Run one attack prompt and score the security outcome."""
    import reference_system.agent as agent_mod

    traces_db = Path(agent_mod._TRACES_DB)

    span_count_before = 0
    if traces_db.exists():
        import sqlite3

        conn = sqlite3.connect(str(traces_db))
        span_count_before = conn.execute("SELECT COUNT(*) FROM spans").fetchone()[0]
        conn.close()

    start = time.monotonic()
    try:
        reply = agent_mod.run(attack_entry["prompt"])
        error = None
    except Exception as exc:  # noqa: BLE001
        reply = ""
        error = f"{type(exc).__name__}: {exc}"
    elapsed_ms = (time.monotonic() - start) * 1000

    # Collect new spans
    spans = []
    if traces_db.exists():
        import sqlite3

        conn = sqlite3.connect(str(traces_db))
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM spans ORDER BY start_ns").fetchall()
        conn.close()
        for row in rows:
            d = dict(row)
            if "attributes" in d and isinstance(d["attributes"], str):
                d["attributes"] = json.loads(d["attributes"])
            spans.append(d)
        spans = spans[span_count_before:]

    # Score security using only the single technique tested
    from agenteval.metrics.security import score_security_run

    result = score_security_run(
        spans,
        guardrail_log_path=str(guardrail_log),
        expected_techniques=[attack_entry["technique_id"]],
    )

    verdict = result.verdicts[0] if result.verdicts else None

    return {
        "attack_name": attack_entry["name"],
        "technique_id": attack_entry["technique_id"],
        "run_index": run_idx,
        "verdict": verdict.verdict if verdict else "UNKNOWN",
        "evidence": verdict.evidence if verdict else "",
        "reply_snippet": reply[:200] if reply else "",
        "error": error,
        "total_ms": round(elapsed_ms, 1),
    }


def _reset_traces_db(db_path: Path) -> None:
    """Delete and recreate the traces DB for a clean run."""
    if db_path.exists():
        db_path.unlink()


def _patch_model(model: str, traces_db: Path, guardrail_log: Path) -> None:
    """Patch the agent module globals to use a specific model and isolated storage."""
    import reference_system.agent as agent_mod
    import reference_system.middleware as middleware_mod

    agent_mod._OLLAMA_MODEL = model
    agent_mod._TRACES_DB = traces_db
    middleware_mod._GUARDRAIL_LOG = guardrail_log


def benchmark_model(model: str) -> dict[str, Any]:
    """Run the full benchmark suite against a single model."""
    print(f"\n{'=' * 60}")
    print(f"  Benchmarking: {model}")
    print(f"{'=' * 60}")

    model_dir = _BENCHMARK_DIR / model.replace(":", "_").replace("/", "_")
    model_dir.mkdir(parents=True, exist_ok=True)
    traces_db = model_dir / "traces.db"
    guardrail_log = model_dir / "guardrail.log"

    _reset_traces_db(traces_db)
    if guardrail_log.exists():
        guardrail_log.unlink()

    _patch_model(model, traces_db, guardrail_log)

    # Warm up
    print(f"  Warming up {model}...")
    if not _warmup_model(model):
        return {"model": model, "error": "warmup_failed", "tasks": [], "attacks": []}

    # --- Task suite ---
    print(f"\n  Running {len(TASK_PROMPTS)} task prompts × {RUNS_PER_PROMPT} runs...")
    task_results: list[dict] = []
    for prompt_entry in TASK_PROMPTS:
        for run_idx in range(RUNS_PER_PROMPT):
            print(
                f"    [{run_idx + 1}/{RUNS_PER_PROMPT}] {prompt_entry['name']}...",
                end=" ",
                flush=True,
            )
            result = _run_single_task(prompt_entry, run_idx)
            status = "✓" if result["passed"] else "✗"
            print(f"{status} ({result['total_ms']:.0f}ms)")
            task_results.append(result)

    # --- Security suite ---
    print(
        f"\n  Running {len(ATTACK_PROMPTS)} attack prompts × {RUNS_PER_PROMPT} runs..."
    )
    attack_results: list[dict] = []
    for attack_entry in ATTACK_PROMPTS:
        # Reset guardrail log between different techniques so scoring
        # doesn't accumulate blocks from unrelated attacks.
        if guardrail_log.exists():
            guardrail_log.unlink()

        for run_idx in range(RUNS_PER_PROMPT):
            print(
                f"    [{run_idx + 1}/{RUNS_PER_PROMPT}] {attack_entry['name']}...",
                end=" ",
                flush=True,
            )
            result = _run_single_attack(attack_entry, guardrail_log, run_idx)
            marker = "✓" if result["verdict"] == "BLOCKED" else "✗"
            print(f"{marker} {result['verdict']} ({result['total_ms']:.0f}ms)")
            attack_results.append(result)

    # --- Aggregate ---
    task_scores = [r["score"] for r in task_results]
    task_pass_rate = sum(1 for r in task_results if r["passed"]) / max(
        len(task_results), 1
    )

    all_latencies = []
    for r in task_results:
        all_latencies.extend(r.get("llm_latencies_ms", []))

    blocked = sum(1 for r in attack_results if r["verdict"] == "BLOCKED")
    total_attacks = len(attack_results)

    # Per-technique median verdict (majority vote across runs)
    from collections import Counter

    technique_verdicts: dict[str, str] = {}
    for tid in ALL_TECHNIQUE_IDS:
        runs_for_tid = [r for r in attack_results if r["technique_id"] == tid]
        if runs_for_tid:
            counts = Counter(r["verdict"] for r in runs_for_tid)
            technique_verdicts[tid] = counts.most_common(1)[0][0]

    summary = {
        "model": model,
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "task_success": {
            "mean_score": round(sum(task_scores) / max(len(task_scores), 1), 3),
            "pass_rate": round(task_pass_rate, 3),
            "total_runs": len(task_results),
        },
        "security": {
            "block_rate": round(blocked / max(total_attacks, 1), 3),
            "blocked": blocked,
            "total": total_attacks,
            "per_technique": technique_verdicts,
        },
        "latency": {
            "median_llm_ms": (
                round(sorted(all_latencies)[len(all_latencies) // 2], 1)
                if all_latencies
                else 0
            ),
            "mean_llm_ms": (
                round(sum(all_latencies) / max(len(all_latencies), 1), 1)
                if all_latencies
                else 0
            ),
            "total_calls": len(all_latencies),
        },
        "task_details": task_results,
        "attack_details": attack_results,
    }

    print(f"\n  Summary for {model}:")
    print(
        f"    Task success:  {summary['task_success']['pass_rate']:.0%} "
        f"pass rate, mean score {summary['task_success']['mean_score']}"
    )
    print(
        f"    Security:      {summary['security']['block_rate']:.0%} "
        f"block rate ({blocked}/{total_attacks})"
    )
    print(f"    Median latency: {summary['latency']['median_llm_ms']}ms per LLM call")

    return summary


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python scripts/benchmark_models.py <model1> [model2] ...")
        print("Example: python scripts/benchmark_models.py llama3.2 llama3.2:1b")
        sys.exit(1)

    models = sys.argv[1:]
    print(f"Benchmarking {len(models)} model(s): {', '.join(models)}")
    print(f"Runs per prompt: {RUNS_PER_PROMPT}")

    _BENCHMARK_DIR.mkdir(parents=True, exist_ok=True)

    results = []
    for model in models:
        result = benchmark_model(model)
        results.append(result)

    # Write aggregate results
    output_path = _REPO_ROOT / "benchmark_results.json"
    report = {
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "runs_per_prompt": RUNS_PER_PROMPT,
        "models": results,
    }
    output_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"\nResults written to {output_path}")

    # Print comparison table
    print(f"\n{'=' * 70}")
    print("  COMPARISON TABLE")
    print(f"{'=' * 70}")
    header = (
        f"{'Model':<25} {'Task Pass%':>10} {'Mean Score':>11} "
        f"{'Block Rate':>11} {'Med. Lat.':>10}"
    )
    print(header)
    print("-" * 70)
    for r in results:
        if r.get("error"):
            print(f"{r['model']:<25} {'ERROR':>10}")
            continue
        print(
            f"{r['model']:<25} "
            f"{r['task_success']['pass_rate']:>9.0%} "
            f"{r['task_success']['mean_score']:>11.3f} "
            f"{r['security']['block_rate']:>10.0%} "
            f"{r['latency']['median_llm_ms']:>9.0f}ms"
        )
    print(f"{'=' * 70}")

    # Per-technique comparison
    print(f"\n{'=' * 70}")
    print("  PER-TECHNIQUE SECURITY VERDICTS")
    print(f"{'=' * 70}")
    techniques = ALL_TECHNIQUE_IDS
    header_parts = [f"{'Technique':<15}"] + [
        f"{r['model']:<15}" for r in results if not r.get("error")
    ]
    print("  ".join(header_parts))
    print("-" * 70)
    for tid in techniques:
        parts = [f"{tid:<15}"]
        for r in results:
            if r.get("error"):
                continue
            verdict = r["security"]["per_technique"].get(tid, "N/A")
            marker = (
                "✓" if verdict == "BLOCKED" else "✗" if verdict == "PASSED" else "~"
            )
            parts.append(f"{marker} {verdict:<12}")
        print("  ".join(parts))
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
