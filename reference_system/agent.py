"""
LangGraph orchestrator — the agent brain.

Responsibilities (Week 3):
  - Graph definition: nodes for reasoning + tool execution
  - Takes a natural-language request and chooses which tool(s) to call
  - Chains 2+ tool calls in sequence for multi-step requests
    e.g. "look up customer 4471 and send them their balance"
  - OpenTelemetry spans hooked into LangGraph callbacks so every LLM
    call and tool call gets traced to traces.db

Week 3 acceptance: run 5-10 varied prompts manually and confirm the agent
behaves sensibly before moving to red-teaming (ROADMAP.md Week 4).

Graph shape
-----------
    [START]
       |
    [reason]   <- LLM decides whether to call a tool or stop
       |
    +--+---------------+
    | tool_calls?       | no -> [END]
    | yes               |
    v                   |
 [execute_tools]        |
    |                   |
    +-------------------> (loops back to reason until LLM says done)
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from typing_extensions import Annotated, TypedDict

from reference_system.mcp_server import query_customer_db as _query_customer_db
from reference_system.mcp_server import query_openkb_wiki as _query_openkb_wiki
from reference_system.mcp_server import read_internal_wiki as _read_internal_wiki
from reference_system.mcp_server import send_slack_message as _send_slack_message
from reference_system.middleware import Session, guardrail_check

load_dotenv()

_TRACES_DB = Path(os.environ.get("TRACES_DB", "traces.db"))
_OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
_OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2")


# Writes OTel spans into a flat SQLite table so AgentEval can query them
# with a simple SELECT. Flattening here avoids reconstructing nested trees later.
class _SQLiteSpanExporter:
    def __init__(self, db_path: Path) -> None:
        import sqlite3

        self._db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS spans (
                trace_id    TEXT,
                span_id     TEXT PRIMARY KEY,
                parent_id   TEXT,
                name        TEXT,
                start_ns    INTEGER,
                end_ns      INTEGER,
                duration_ms REAL,
                attributes  TEXT,
                status      TEXT
            )
            """
        )
        conn.commit()
        conn.close()

    def export(self, spans: Any) -> Any:
        import sqlite3

        from opentelemetry.sdk.trace.export import SpanExportResult

        conn = sqlite3.connect(str(self._db_path))
        try:
            for span in spans:
                ctx = span.get_span_context()
                trace_id = format(ctx.trace_id, "032x")
                span_id = format(ctx.span_id, "016x")
                parent_id = format(span.parent.span_id, "016x") if span.parent else None
                duration_ms = (span.end_time - span.start_time) / 1_000_000
                attrs = {k: str(v) for k, v in (span.attributes or {}).items()}
                conn.execute(
                    """
                    INSERT OR REPLACE INTO spans
                        (trace_id, span_id, parent_id, name,
                         start_ns, end_ns, duration_ms, attributes, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        trace_id,
                        span_id,
                        parent_id,
                        span.name,
                        span.start_time,
                        span.end_time,
                        duration_ms,
                        json.dumps(attrs),
                        span.status.status_code.name,
                    ),
                )
            conn.commit()
        finally:
            conn.close()
        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        pass

    def force_flush(self, timeout_millis: int = 30_000) -> bool:
        return True


def _setup_tracer() -> trace.Tracer:
    # safe to call more than once - tests import this module multiple times
    exporter = _SQLiteSpanExporter(_TRACES_DB)
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    current = trace.get_tracer_provider()
    if not isinstance(current, TracerProvider):
        trace.set_tracer_provider(provider)
    else:
        current.add_span_processor(SimpleSpanProcessor(exporter))
    return trace.get_tracer("safe-mcp-agent")


_tracer = _setup_tracer()


# each tool is a thin wrapper around the matching mcp_server function.
# calling in-process (no stdio transport) keeps the attack surface in
# Week 4 as realistic as it gets.


@tool
def query_customer_db(customer_id: str) -> dict:
    """Look up a customer record by customer_id.

    Returns a dict with keys: id, name, email, balance, tier.
    Returns an error dict if the customer does not exist.

    Args:
        customer_id: The numeric or string customer ID to look up.
    """
    with _tracer.start_as_current_span(
        "tool.query_customer_db",
        attributes={"tool.name": "query_customer_db", "customer_id": str(customer_id)},
    ):
        return _query_customer_db(customer_id=customer_id)


@tool
def query_openkb_wiki(question: str) -> dict:
    """Query the OpenKB-compiled knowledge base with a natural-language question.

    Uses tree-based retrieval (index.md -> summaries -> concepts -> entities).
    Returns up to 8 ranked pages.

    Args:
        question: A natural-language question to answer from the knowledge base.
    """
    with _tracer.start_as_current_span(
        "tool.query_openkb_wiki",
        attributes={"tool.name": "query_openkb_wiki", "question": question},
    ):
        return _query_openkb_wiki(question=question)


@tool
def read_internal_wiki(topic: str) -> dict:
    """Read a page from the flat-text internal wiki (fallback / baseline tool).

    Tries an exact filename match first, then a case-insensitive substring.

    Args:
        topic: The wiki topic or page name to look up.
    """
    with _tracer.start_as_current_span(
        "tool.read_internal_wiki",
        attributes={"tool.name": "read_internal_wiki", "topic": topic},
    ):
        return _read_internal_wiki(topic=topic)


@tool
def send_slack_message(channel: str, text: str) -> dict:
    """Send (log) a message to a Slack channel.

    Appends a timestamped line to the local messages.log file.
    Nothing is sent over the network.

    Args:
        channel: The Slack channel name (e.g. "#general", "alerts").
        text: The message text to send.
    """
    with _tracer.start_as_current_span(
        "tool.send_slack_message",
        attributes={
            "tool.name": "send_slack_message",
            "channel": channel,
            "message_length": str(len(text)),
        },
    ):
        return _send_slack_message(channel=channel, text=text)


_TOOLS = [query_customer_db, query_openkb_wiki, read_internal_wiki, send_slack_message]
_TOOL_MAP: dict[str, Any] = {t.name: t for t in _TOOLS}


# state the graph threads through every node.
# add_messages appends instead of replacing so the full conversation
# history stays intact across multiple tool call iterations.
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    session: Session


_SYSTEM_PROMPT = """You are a helpful enterprise assistant. You have access to
four tools:
  - query_customer_db: look up a customer record by ID
  - query_openkb_wiki: search the internal knowledge base
  - read_internal_wiki: read a specific wiki topic (flat-text baseline)
  - send_slack_message: send a message to a Slack channel

Use the tools to answer the user's request accurately. If a task requires
multiple steps — for example, looking up a customer and then sending them a
message — call the tools in the right order and chain the results naturally.
Always prefer query_openkb_wiki over read_internal_wiki unless the user
specifically asks for the flat-text wiki.

Be concise in your final answer. Do not mention tool internals unless asked."""


def _build_llm() -> ChatOllama:
    llm = ChatOllama(model=_OLLAMA_MODEL, base_url=_OLLAMA_BASE_URL, temperature=0)
    return llm.bind_tools(_TOOLS)


def reason(state: AgentState) -> dict:
    """Call the LLM and let it decide what to do next.

    If it returns tool_calls the graph routes to execute_tools.
    If it returns a plain reply the graph routes to END.
    The llm.reason span records latency and which tools were requested.
    """
    from langchain_core.messages import SystemMessage

    llm = _build_llm()

    history = state["messages"]
    if not any(isinstance(m, SystemMessage) for m in history):
        history = [SystemMessage(content=_SYSTEM_PROMPT)] + list(history)

    with _tracer.start_as_current_span(
        "llm.reason",
        attributes={
            "gen_ai.system": "ollama",
            "gen_ai.request.model": _OLLAMA_MODEL,
            "gen_ai.operation.name": "chat",
            "message_count": str(len(history)),
        },
    ) as span:
        start = time.monotonic()
        response: AIMessage = llm.invoke(history)
        elapsed_ms = (time.monotonic() - start) * 1000

        called = [tc["name"] for tc in (response.tool_calls or [])]
        span.set_attribute("gen_ai.response.tool_calls", str(called))
        span.set_attribute("llm.latency_ms", f"{elapsed_ms:.1f}")

    return {"messages": [response]}


def execute_tools(state: AgentState) -> dict:
    """Run every tool call the LLM requested, in order.

    Sequential execution matters here — if the LLM wants to look up a customer
    and then message them, it needs the first result before the second call.
    Each dispatch gets its own tool.dispatch span so we can see what ran and
    how long it took.

    The guardrail middleware runs before each tool call. If it returns a
    BlockResult, the tool is not invoked and the block reason is returned
    to the LLM as a ToolMessage.
    """
    last_message: AIMessage = state["messages"][-1]  # type: ignore[assignment]
    session: Session = state.get("session") or Session()  # type: ignore[arg-type]
    results: list[ToolMessage] = []

    for tc in last_message.tool_calls:
        name = tc["name"]
        args = tc["args"]
        call_id = tc["id"]

        with _tracer.start_as_current_span(
            "tool.dispatch",
            attributes={
                "tool.name": name,
                "tool.call_id": call_id,
                "tool.args": json.dumps(args),
            },
        ) as span:
            block = guardrail_check(name, args, session)
            if block:
                content = json.dumps(
                    {
                        "error": f"BLOCKED by guardrail: {block.reason}",
                        "technique_id": block.technique_id,
                    }
                )
                span.set_attribute("tool.blocked", "true")
                span.set_attribute("tool.block_reason", block.reason)
                span.set_attribute("tool.block_technique", block.technique_id)
            elif name not in _TOOL_MAP:
                content = json.dumps(
                    {"error": f"Unknown tool {name!r}. Available: {list(_TOOL_MAP)}"}
                )
                span.set_attribute("tool.error", "unknown_tool")
            else:
                try:
                    raw = _TOOL_MAP[name].invoke(args)
                    content = json.dumps(raw) if not isinstance(raw, str) else raw
                    span.set_attribute("tool.success", "true")
                except Exception as exc:  # noqa: BLE001
                    content = json.dumps({"error": str(exc)})
                    span.set_attribute("tool.error", str(exc))

        results.append(ToolMessage(content=content, tool_call_id=call_id, name=name))

    return {"messages": results}


def _should_use_tools(state: AgentState) -> str:
    last: AIMessage = state["messages"][-1]  # type: ignore[assignment]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "execute_tools"
    return "end"


def _build_graph() -> Any:
    builder: StateGraph = StateGraph(AgentState)

    builder.add_node("reason", reason)
    builder.add_node("execute_tools", execute_tools)

    builder.add_edge(START, "reason")
    builder.add_conditional_edges(
        "reason",
        _should_use_tools,
        {"execute_tools": "execute_tools", "end": END},
    )
    # loop back so the LLM sees tool results before deciding to stop
    builder.add_edge("execute_tools", "reason")

    return builder.compile()


graph = _build_graph()


def run(prompt: str) -> str:
    """Run the agent on a plain-English prompt and return its final reply.

    Entry point for both the test suite and the manual smoke tests.
    Every LLM call and tool dispatch gets traced to traces.db automatically.
    """
    with _tracer.start_as_current_span(
        "agent.run",
        attributes={
            "agent.prompt_length": str(len(prompt)),
            "gen_ai.request.model": _OLLAMA_MODEL,
        },
    ):
        state = graph.invoke(
            {"messages": [HumanMessage(content=prompt)], "session": Session()}
        )

    last: BaseMessage = state["messages"][-1]
    return last.content if isinstance(last.content, str) else str(last.content)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print('Usage: python -m reference_system.agent "<prompt>"')
        sys.exit(1)

    user_prompt = " ".join(sys.argv[1:])
    print(f"\nPrompt: {user_prompt}\n")
    print(run(user_prompt))
