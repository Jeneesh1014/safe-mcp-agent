# mcp-guardeval

Automated evaluation library for MCP-based LLM agents.

```bash
pip install mcp-guardeval
```

Provides:
- **Task success scoring** — did the agent complete the requested task?
- **Security evaluation** — did any SAFE-MCP attack technique get through?
- **OpenTelemetry trace analysis** — normalises OTel spans into flat SQLite rows for fast querying
- **pytest plugin** — run the full attack suite with `pytest --agenteval`

## Quick usage

```python
from agenteval.metrics.task_success import score_task
from agenteval.metrics.security import score_security_run
from agenteval.storage import TraceStore

store = TraceStore("traces.db")
result = score_task(store, run_id="abc123", expected_tools=["query_customer_db"])
```

## pytest plugin

```bash
pytest tests/test_security.py --agenteval -v
```

## License

MIT
