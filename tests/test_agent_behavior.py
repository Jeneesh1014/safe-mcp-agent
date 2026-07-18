"""
Agent behaviour tests.

Verifies that the agent correctly completes legitimate tasks before we start
red-teaming it. Passing these first is the acceptance criterion for Week 3.

Test naming convention: test_<scenario>_<expected_outcome>
"""

import pytest


@pytest.mark.slow
def test_single_tool_customer_lookup():
    """Agent can look up a customer by ID and return their name and balance."""
    # TODO(week-3): implement
    pytest.skip("Not implemented yet — Week 3 target")


@pytest.mark.slow
def test_chained_tool_lookup_then_message():
    """
    Agent chains two tool calls: query_customer_db then send_slack_message.
    Scenario: 'Look up customer 4471 and notify #billing of their balance.'
    """
    # TODO(week-3): implement
    pytest.skip("Not implemented yet — Week 3 target")


@pytest.mark.slow
def test_three_tool_chain():
    """
    Agent chains three tool calls in sequence for a multi-step request.
    Scenario: look up customer, read billing policy, compose a support message.
    """
    # TODO(week-3): implement
    pytest.skip("Not implemented yet — Week 3 target")
