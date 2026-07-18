"""
MCP server — exposes three mock enterprise tools.

Tools (Week 2):
  - query_customer_db(customer_id)   reads from the seeded SQLite DB
  - read_internal_wiki(topic)         reads from local text files
  - send_slack_message(channel, text) appends to a local log file

No security validation lives here intentionally. That is the middleware's job.
Week 2 target: all three tools callable, returning realistic-looking mock data.
"""

# TODO(week-2): implement MCP server with three tools
