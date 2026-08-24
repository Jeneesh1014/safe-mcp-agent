"""
Week 3 manual smoke test.

Run this before moving on to Week 4 red-teaming:
    python scripts/smoke_test_week3.py

Prints each prompt, the agent's reply, and a PASS/FAIL verdict.
All calls are traced to traces.db automatically via the OTel exporter
in agent.py.

You don't need Ollama running for imports; it only matters when run() fires.
"""

import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from reference_system.agent import run  # noqa: E402
from reference_system.mcp_server import _LOG_PATH  # noqa: E402

GREEN = "\033[32m"
RED = "\033[31m"
RESET = "\033[0m"
BOLD = "\033[1m"

TESTS = [
    # (label, prompt, required_keywords_in_reply)
    (
        "single tool — customer lookup",
        "What is the name and account balance of customer 4471?",
        ["amara", "1420"],
    ),
    (
        "single tool — wiki question",
        "What is the billing policy?",
        ["bill"],
    ),
    (
        "single tool — flat wiki fallback",
        "Read the internal wiki page about support escalation.",
        ["escalat"],
    ),
    (
        "2-step chain — lookup then Slack",
        "Look up customer 1182 and send their balance to #finance on Slack.",
        ["320", "leon", "brandt"],
    ),
    (
        "2-step chain — lookup then Slack (enterprise tier)",
        "Look up customer 9903 and message #enterprise-accounts with their tier.",
        ["enterprise", "priya"],
    ),
    (
        "error handling — missing customer",
        "What is the email for customer 9999999?",
        ["not found", "error", "9999999"],
    ),
    (
        "error handling — zero balance customer",
        "What is the balance of customer 0055?",
        ["0", "carlos", "rivera"],
    ),
    (
        "knowledge base — open-ended question",
        "How should I handle a data breach under company policy?",
        ["data", "breach", "report", "incident", "security"],
    ),
    (
        "multi-hop — lookup + wiki + Slack",
        (
            "Look up customer 7731, check the billing policy, "
            "then send a summary to #billing."
        ),
        ["ingrid", "johansson", "5200"],
    ),
    (
        "tool selection — prefer openkb over flat wiki",
        "Tell me about the company's data handling procedures.",
        ["data"],
    ),
]


def verdict(reply: str, keywords: list[str]) -> bool:
    lower = reply.lower()
    return any(k.lower() in lower for k in keywords)


def main() -> None:
    passed = 0
    failed = 0

    print(f"\n{BOLD}Week 3 smoke test — {len(TESTS)} prompts{RESET}\n")

    log_size_before = _LOG_PATH.stat().st_size if _LOG_PATH.exists() else 0

    for i, (label, prompt, keywords) in enumerate(TESTS, 1):
        print(f"{BOLD}[{i}/{len(TESTS)}] {label}{RESET}")
        print(f"  Prompt: {prompt}")
        try:
            reply = run(prompt)
        except Exception as exc:
            reply = f"<exception: {exc}>"

        short = textwrap.shorten(reply, width=120, placeholder="...")
        print(f"  Reply:  {short}")

        ok = verdict(reply, keywords)
        if ok:
            print(f"  {GREEN}PASS{RESET}")
            passed += 1
        else:
            print(f"  {RED}FAIL{RESET}  (wanted one of: {keywords})")
            failed += 1
        print()

    log_size_after = _LOG_PATH.stat().st_size if _LOG_PATH.exists() else 0
    slack_entries = log_size_after - log_size_before
    print(
        f"Slack log grew by {slack_entries} bytes (Slack calls logged to {_LOG_PATH})"
    )
    print(f"\n{BOLD}Result: {passed} passed, {failed} failed{RESET}\n")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
