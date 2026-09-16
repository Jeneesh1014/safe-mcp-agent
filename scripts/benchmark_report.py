"""
Benchmark report generator — reads benchmark_results.json and produces
a Markdown report at benchmark_report.md.

Usage:
    python scripts/benchmark_report.py
    python scripts/benchmark_report.py path/to/benchmark_results.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_results(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _median(values: list[float]) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    return s[len(s) // 2]


def _generate_report(data: dict) -> str:
    models: list[dict[str, Any]] = data["models"]
    runs_per_prompt = data.get("runs_per_prompt", "?")

    lines: list[str] = []
    w = lines.append

    w("# Benchmark Report — Model Comparison")
    w("")
    w(f"Generated: {data['generated_at']}")
    w(f"Runs per prompt: {runs_per_prompt}")
    w("")

    # --- Summary table ---
    w("## Summary")
    w("")
    w(
        "| Model | Task Pass Rate | Mean Task Score | "
        "Security Block Rate | Median LLM Latency |"
    )
    w("|---|---|---|---|---|")
    for m in models:
        if m.get("error"):
            w(f"| {m['model']} | ERROR | — | — | — |")
            continue
        ts = m["task_success"]
        sec = m["security"]
        lat = m["latency"]
        pass_count = int(ts["pass_rate"] * ts["total_runs"])
        total_runs = ts["total_runs"]
        w(
            f"| {m['model']} "
            f"| {ts['pass_rate']:.0%} ({pass_count}/{total_runs}) "
            f"| {ts['mean_score']:.3f} "
            f"| {sec['block_rate']:.0%} ({sec['blocked']}/{sec['total']}) "
            f"| {lat['median_llm_ms']:.0f} ms |"
        )
    w("")

    # --- Per-technique security comparison ---
    w("## Security: Per-Technique Verdicts")
    w("")
    valid_models = [m for m in models if not m.get("error")]
    header_cols = ["Technique"] + [m["model"] for m in valid_models]
    w("| " + " | ".join(header_cols) + " |")
    w("| " + " | ".join(["---"] * len(header_cols)) + " |")

    if valid_models:
        all_techniques = sorted(
            {tid for m in valid_models for tid in m["security"]["per_technique"]}
        )
        for tid in all_techniques:
            cols = [tid]
            for m in valid_models:
                verdict = m["security"]["per_technique"].get(tid, "N/A")
                emoji = (
                    "✅"
                    if verdict == "BLOCKED"
                    else "❌" if verdict == "PASSED" else "⚠️"
                )
                cols.append(f"{emoji} {verdict}")
            w("| " + " | ".join(cols) + " |")
    w("")

    # --- Task success details per model ---
    w("## Task Success: Per-Prompt Breakdown")
    w("")
    for m in valid_models:
        w(f"### {m['model']}")
        w("")
        w("| Prompt | Pass Rate | Mean Score | Median Latency |")
        w("|---|---|---|---|")

        # Group task details by prompt name
        by_prompt: dict[str, list[dict]] = {}
        for td in m.get("task_details", []):
            by_prompt.setdefault(td["prompt_name"], []).append(td)

        for pname, runs in by_prompt.items():
            pass_count = sum(1 for r in runs if r["passed"])
            mean_score = sum(r["score"] for r in runs) / max(len(runs), 1)
            all_lat = []
            for r in runs:
                all_lat.extend(r.get("llm_latencies_ms", []))
            med_lat = _median(all_lat)
            w(
                f"| {pname} "
                f"| {pass_count}/{len(runs)} "
                f"| {mean_score:.3f} "
                f"| {med_lat:.0f} ms |"
            )
        w("")

    # --- Latency comparison ---
    w("## Latency Comparison")
    w("")
    w("| Model | Median LLM Call | Mean LLM Call | Total LLM Calls |")
    w("|---|---|---|---|")
    for m in valid_models:
        lat = m["latency"]
        w(
            f"| {m['model']} "
            f"| {lat['median_llm_ms']:.0f} ms "
            f"| {lat['mean_llm_ms']:.0f} ms "
            f"| {lat['total_calls']} |"
        )
    w("")

    # --- Key findings (template) ---
    w("## Key Findings")
    w("")
    w("> **Fill this section in after reviewing the results above.**")
    w(">")
    w("> Questions to answer:")
    w("> - Does the smaller/quantized model have lower task success?")
    w("> - Does it change how often the guardrail catches attacks?")
    w("> - Does the model itself attempt unsafe actions more or less often?")
    w("> - How does latency scale with model size?")
    w("")

    return "\n".join(lines)


def main() -> None:
    results_path = _REPO_ROOT / "benchmark_results.json"
    if len(sys.argv) > 1:
        results_path = Path(sys.argv[1])

    if not results_path.exists():
        print(f"Results file not found: {results_path}")
        print("Run `python scripts/benchmark_models.py` first.")
        sys.exit(1)

    data = _load_results(results_path)
    report = _generate_report(data)

    output_path = _REPO_ROOT / "benchmark_report.md"
    output_path.write_text(report, encoding="utf-8")
    print(f"Report written to {output_path}")
    print(f"  Models: {len(data['models'])}")
    print(f"  Generated: {data['generated_at']}")


if __name__ == "__main__":
    main()
