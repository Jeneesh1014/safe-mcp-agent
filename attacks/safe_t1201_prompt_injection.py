"""
Attack script: SAFE-T1201 — Prompt Injection to Hijack Tool Selection.

Technique summary:
  An attacker embeds instructions in user-supplied data (e.g. a customer name
  or a wiki page) that redirect the agent's tool selection away from the
  legitimate task. Goal: get the agent to call a tool it was not asked to call,
  or with arguments it was not asked to use.

Week 4 target:
  1. Run this against the UNDEFENDED Week 3 agent and confirm the attack succeeds.
  2. Document what the agent actually did (which tool it called, with what args).
  3. Re-run in Week 5 after middleware is in place and confirm it is blocked.

Usage:
    python attacks/safe_t1201_prompt_injection.py
"""

# TODO(week-4): implement attack script
