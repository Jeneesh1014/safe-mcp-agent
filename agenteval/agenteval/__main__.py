"""
CLI entrypoint — ``python -m agenteval``.

Prints the same summary report as the pytest plugin, without requiring
a test suite.  Useful for quick verification or CI scripts that don't
use pytest.

Usage::

    python -m agenteval                          # defaults
    python -m agenteval --db traces.db --log guardrail.log
    python -m agenteval --threshold 0.85
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from agenteval import __version__


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agenteval",
        description=(
            "Evaluate MCP agent traces for task success and security" " resilience."
        ),
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
        "--db",
        default=os.environ.get("TRACES_DB", "traces.db"),
        help="Path to the OpenTelemetry traces SQLite database (default: traces.db).",
    )
    parser.add_argument(
        "--log",
        default=os.environ.get("GUARDRAIL_LOG", "guardrail.log"),
        help="Path to the guardrail JSONL log file (default: guardrail.log).",
    )
    parser.add_argument(
        "--techniques",
        nargs="*",
        default=[],
        help="Technique IDs to evaluate. Auto-discovered from log if omitted.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.0,
        help="Minimum block rate (0.0–1.0) to consider the run secure.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the evaluation and print a summary report. Returns 0 on success."""
    args = _build_parser().parse_args(argv)

    # Lazy imports so --help and --version stay fast.
    from agenteval.metrics.security import score_security_run
    from agenteval.storage import TraceStore, discover_techniques

    db_path = Path(args.db)
    log_path = Path(args.log)

    print(f"agenteval {__version__}")
    print("=" * 60)

    if not db_path.exists():
        print(f"  ✗ traces.db not found at {db_path}")
        return 1

    store = TraceStore(db_path)
    all_traces = store.get_all_traces()
    print(f"  Traces in DB: {len(all_traces)}")

    all_spans: list[dict] = []
    for trace_id in all_traces:
        all_spans.extend(store.get_spans_by_trace(trace_id))

    dispatch_spans = [s for s in all_spans if s.get("name") == "tool.dispatch"]
    blocked_spans = [
        s
        for s in dispatch_spans
        if s.get("attributes", {}).get("tool.blocked") == "true"
    ]
    print(f"  Tool dispatches: {len(dispatch_spans)}")
    print(f"  Blocked by guardrail: {len(blocked_spans)}")

    if not log_path.exists():
        print(f"  Guardrail log not found at {log_path}")
        print("=" * 60)
        return 0

    techniques = list(args.techniques)
    if not techniques:
        techniques = discover_techniques(log_path)
        if techniques:
            print(f"  Auto-discovered {len(techniques)} techniques from log")

    if not techniques:
        print("  No techniques configured or discovered — skipping security scoring")
        print("=" * 60)
        return 0

    result = score_security_run(
        spans=all_spans,
        guardrail_log_path=str(log_path),
        expected_techniques=techniques,
    )

    print(
        f"  Block rate: {result.block_rate:.0%} "
        f"({result.blocked_count}/{result.total_attacks})"
    )
    print()
    for v in result.verdicts:
        if v.verdict == "BLOCKED":
            marker = "✓"
        elif v.verdict == "PASSED":
            marker = "✗"
        else:
            marker = "~"
        print(f"    {marker} {v.technique_id}: {v.verdict}")

    if args.threshold > 0.0:
        print()
        if result.block_rate >= args.threshold:
            print(
                f"  ✓ Block rate {result.block_rate:.0%} "
                f"meets threshold {args.threshold:.0%}"
            )
        else:
            print(
                f"  ✗ Block rate {result.block_rate:.0%} "
                f"below threshold {args.threshold:.0%}"
            )
            print("=" * 60)
            return 1

    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
