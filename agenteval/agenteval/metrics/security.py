"""
Security metric — did an attack get through, which ones, and how often?

Scores a test run by reading the guardrail's structured log entries and
classifying each attack attempt as:
  - BLOCKED   : guardrail logged a rejection with the correct technique ID
  - PASSED    : the attack reached the tool and executed
  - PARTIAL   : the tool call was made but the sensitive operation failed
    downstream (counts as a miss — the guardrail didn't catch it)
"""
from __future__ import annotations

# TODO(week-6): implement score_security_run
