"""
SQLite read/write layer.

Owns all queries against traces.db. Nothing outside this module
should construct raw SQL for traces.db.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


class TraceStore:
    """Read-only interface to an existing traces.db written by
    the agent's span exporter.
    """

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path)
        if not self._db_path.exists():
            raise FileNotFoundError(f"traces.db not found: {self._db_path}")

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _rows_to_dicts(self, rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
        results = []
        for row in rows:
            d = dict(row)
            if "attributes" in d and isinstance(d["attributes"], str):
                d["attributes"] = json.loads(d["attributes"])
            results.append(d)
        return results

    def get_all_traces(self) -> list[str]:
        conn = self._connect()
        try:
            rows = conn.execute("SELECT DISTINCT trace_id FROM spans").fetchall()
            return [row["trace_id"] for row in rows]
        finally:
            conn.close()

    def get_spans_by_trace(self, trace_id: str) -> list[dict[str, Any]]:
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT * FROM spans WHERE trace_id = ? ORDER BY start_ns",
                (trace_id,),
            ).fetchall()
            return self._rows_to_dicts(rows)
        finally:
            conn.close()

    def get_spans_by_name(self, name: str) -> list[dict[str, Any]]:
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT * FROM spans WHERE name = ? ORDER BY start_ns",
                (name,),
            ).fetchall()
            return self._rows_to_dicts(rows)
        finally:
            conn.close()

    def get_spans_for_run(self, run_span_id: str) -> list[dict[str, Any]]:
        """All spans belonging to a single agent.run invocation (by parent chain)."""
        conn = self._connect()
        try:
            run_row = conn.execute(
                "SELECT * FROM spans WHERE span_id = ?", (run_span_id,)
            ).fetchone()
            if not run_row:
                return []

            trace_id = run_row["trace_id"]
            rows = conn.execute(
                "SELECT * FROM spans WHERE trace_id = ? ORDER BY start_ns",
                (trace_id,),
            ).fetchall()
            return self._rows_to_dicts(rows)
        finally:
            conn.close()


def load_guardrail_log(
    log_path: str | Path,
    technique_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Parse the JSONL guardrail log into a list of dicts.

    Args:
        log_path: path to the JSONL guardrail log file.
        technique_ids: if provided, only return entries whose ``technique_id``
            is in this set.  Pass ``None`` to return everything.
    """
    path = Path(log_path)
    if not path.exists():
        return []

    entries: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        entry = json.loads(line)
        if technique_ids is not None and entry.get("technique_id") not in technique_ids:
            continue
        entries.append(entry)
    return entries


def discover_techniques(log_path: str | Path) -> list[str]:
    """Extract unique technique IDs from a guardrail JSONL log.

    Useful for auto-configuring the evaluation plugin when no explicit
    technique list is provided — the log itself becomes the catalog.
    """
    path = Path(log_path)
    if not path.exists():
        return []

    seen: dict[str, None] = {}  # preserves insertion order
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        entry = json.loads(line)
        tid = entry.get("technique_id")
        if tid and tid not in seen:
            seen[tid] = None
    return list(seen)
