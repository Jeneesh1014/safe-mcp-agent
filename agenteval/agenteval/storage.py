"""
SQLite read/write layer.

Owns the traces.db schema and all queries against it.
Nothing outside this module should construct raw SQL for traces.db.
"""
from __future__ import annotations

from pathlib import Path

# TODO(week-6): implement TraceStore
