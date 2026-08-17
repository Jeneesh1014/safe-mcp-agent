"""
Week 2 smoke test — calls each MCP tool directly and prints results.

Run from the repo root:
    python scripts/smoke_test_week2.py

All four tools should return sensible data. If any tool fails, the script
prints the error and exits with code 1.
"""

from __future__ import annotations

import sys

sys.path.insert(0, ".")

from reference_system.mcp_server import (  # noqa: E402
    query_customer_db,
    query_openkb_wiki,
    read_internal_wiki,
    send_slack_message,
)

PASS = "\033[92m✓\033[0m"
FAIL = "\033[91m✗\033[0m"
failed = False


def check(label: str, result: dict, must_have_key: str) -> None:
    global failed
    if "error" in result and must_have_key not in result:
        print(f"{FAIL}  {label}")
        print(f"     {result}")
        failed = True
    elif must_have_key in result:
        print(f"{PASS}  {label}")
    else:
        print(f"{FAIL}  {label} — key {must_have_key!r} missing")
        print(f"     {result}")
        failed = True


print("\n=== query_customer_db ===")

r = query_customer_db("4471")
check("customer 4471 (Amara Nwosu, premium)", r, "name")
assert r.get("name") == "Amara Nwosu", f"unexpected: {r}"

r = query_customer_db("9903")
check("customer 9903 (Priya Mehta, enterprise)", r, "name")
assert r.get("tier") == "enterprise", f"unexpected: {r}"

r = query_customer_db("0055")
check("customer 0055 (Carlos Rivera, zero balance)", r, "name")
assert r.get("balance") == 0.0, f"unexpected: {r}"

r = query_customer_db("9999")
check("customer 9999 (not found — error expected)", r, "error")

print("\n=== read_internal_wiki ===")

r = read_internal_wiki("billing")
check("billing page (exact match)", r, "content")
assert "Invoice" in r.get("content", ""), f"unexpected content: {r}"

r = read_internal_wiki("data")
check("data_handling page (substring match)", r, "content")

r = read_internal_wiki("escalation")
check("support_escalation page (substring match)", r, "content")

r = read_internal_wiki("doesnotexist")
check("missing topic (available_topics returned)", r, "available_topics")

print("\n=== send_slack_message ===")

r = send_slack_message("general", "Smoke test message from Week 2 script")
check("log to #general", r, "status")
assert r.get("status") == "logged", f"unexpected: {r}"

r = send_slack_message("alerts", "Second test message — multi-channel logging")
check("log to #alerts", r, "status")

print("\n=== query_openkb_wiki (tree-based retrieval) ===")

r = query_openkb_wiki("access control policy")
check("access control — basic retrieval", r, "results")
pages = [hit["page"] for hit in r["results"]]
print(f"     pages returned: {pages}")
assert any("access" in p for p in pages), f"expected access-related pages, got: {pages}"

r = query_openkb_wiki("how should billing disputes be handled and escalated")
check("billing dispute — multi-hop", r, "results")
pages = [hit["page"] for hit in r["results"]]
print(f"     pages returned: {pages}")

r = query_openkb_wiki("what customer data is confidential and restricted")
check("customer data classification — multi-hop", r, "results")
pages = [hit["page"] for hit in r["results"]]
print(f"     pages returned: {pages}")
assert any(
    "customer" in p or "data" in p or "infosec" in p for p in pages
), f"expected data-related pages, got: {pages}"

r = query_openkb_wiki("completely unrelated nonsense xyz")
check("no-match query (index fallback)", r, "results")

print()
if failed:
    print("Some checks failed — see above.")
    sys.exit(1)
else:
    print("All smoke tests passed.")
    sys.exit(0)
