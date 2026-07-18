"""
Security test suite — runs all attack scripts and asserts the guardrail
catches them.

Each test is parametrized over one SAFE-MCP technique and asserts that:
  1. The attack script reaches the guardrail (i.e. the agent attempts the call).
  2. The guardrail logs a block event with the correct technique ID.
  3. The tool is NOT actually executed.

Test names follow: test_guardrail_blocks_<technique_description>

Run with: pytest tests/test_security.py --agenteval -v
"""
import pytest


@pytest.mark.slow
@pytest.mark.security
def test_guardrail_blocks_prompt_injection_tool_hijack():
    """SAFE-T1201: injected prompt that tries to redirect tool selection."""
    # TODO(week-5/6): implement once middleware and agenteval are wired up
    pytest.skip("Not implemented yet — Week 5/6 target")


@pytest.mark.slow
@pytest.mark.security
def test_guardrail_blocks_tool_argument_hijacking():
    """SAFE-T1203: malformed arguments designed to overload tool parameter parsing."""
    # TODO(week-5/6): implement
    pytest.skip("Not implemented yet — Week 5/6 target")


@pytest.mark.slow
@pytest.mark.security
def test_guardrail_blocks_data_exfiltration_via_slack():
    """
    SAFE-T1208: attack that attempts to exfiltrate customer PII by embedding
    it in a send_slack_message call.

    # SAFE-T1208: block outbound tool calls carrying anything that looks like a
    # credential or account token, not just exact string matches on "password".
    """
    # TODO(week-5/6): implement
    pytest.skip("Not implemented yet — Week 5/6 target")
