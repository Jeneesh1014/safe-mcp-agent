"""
Trace processor — normalises OpenTelemetry spans into flat SQLite rows.

Design rule: store flat rows, not nested trace trees.
Nested trees are natural for OTel but make queries slow.
Flatten at ingestion; query fast.
"""

from __future__ import annotations

# TODO(week-6): implement trace_processor
