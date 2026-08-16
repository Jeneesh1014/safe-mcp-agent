"""
MCP server — four enterprise tools used by the Week 3 LangGraph agent.

Tools
-----
query_customer_db(customer_id)
    Look up a customer record by ID from the seeded SQLite database.

query_openkb_wiki(question)
    Query the OpenKB-compiled knowledge base using tree-based retrieval.
    Navigates index.md then follows [[wikilinks]] into summaries, concepts,
    and entities rather than doing blind text chunking.

read_internal_wiki(topic)
    Flat-text fallback reader. Reads .txt files from fixtures/wiki/.
    Kept deliberately simple for Week 7 benchmarking against the OpenKB tool.

send_slack_message(channel, text)
    Appends a timestamped line to fixtures/messages.log.
    Does not send anything over the network.

Security note
-------------
There is no input validation in this file on purpose. Validation and
permission scoping belong in middleware.py (Week 5). Keeping this file
open allows the Week 4 red-team exercises to actually work against a
realistic target.
"""

from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

_HERE = Path(__file__).parent
_FIXTURES = _HERE / "fixtures"
_DB_PATH = _FIXTURES / "customers.db"
_WIKI_DIR = _FIXTURES / "wiki"
_LOG_PATH = _FIXTURES / "messages.log"
_OPENKB_DIR = _HERE.parent / "wiki"

mcp = FastMCP("safe-mcp-agent")


class CustomerQuery(BaseModel):
    """Input schema for query_customer_db."""

    customer_id: str


class WikiQuery(BaseModel):
    """Input schema for query_openkb_wiki."""

    question: str


class InternalWikiQuery(BaseModel):
    """Input schema for read_internal_wiki."""

    topic: str


class SlackMessage(BaseModel):
    """Input schema for send_slack_message."""

    channel: str
    text: str


@mcp.tool()
def query_customer_db(customer_id: str) -> dict[str, Any]:
    """
    Look up a customer record by customer_id.

    Returns a dict with keys: id, name, email, balance, tier.
    Returns an error dict if the customer does not exist or the DB is missing.
    """
    if not _DB_PATH.exists():
        return {
            "error": (
                f"Database not found at {_DB_PATH}. "
                "Run `python scripts/seed_fixtures.py` first."
            )
        }

    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT id, name, email, balance, tier FROM customers WHERE id = ?",
            (str(customer_id),),
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        return {"error": f"No customer found with id={customer_id!r}"}

    return {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "balance": row["balance"],
        "tier": row["tier"],
    }


def _strip_frontmatter(text: str) -> str:
    """Remove YAML frontmatter (--- ... ---) from the top of a markdown file."""
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            return text[end + 3 :].lstrip("\n")
    return text


def _keyword_score(text: str, keywords: list[str]) -> int:
    """Count total keyword occurrences in text (case-insensitive)."""
    lower = text.lower()
    return sum(lower.count(kw) for kw in keywords)


def _run_tree_retrieval(question: str) -> list[dict[str, str]]:
    """
    Walk the OpenKB wiki graph and return ranked pages for a question.

    Steps:
    1.  Read index.md and collect every [[wikilink]] listed there.
    2.  Always include all summaries/ pages as primary candidates because
        they are the highest-signal entry points in the compiled wiki.
    3.  Score each candidate page by counting question keyword hits.
    4.  Take the top five pages by score.
    5.  For each of those pages, follow any [[wikilinks]] inside them to
        reach related concepts and entities (one level of expansion).
    6.  Return a ranked list of up to eight pages with their content.

    Why not blind chunking?
    The OpenKB wiki compiles documents into a structured graph:
    sources → summaries → concepts → entities. Following that graph
    gives better precision than splitting text into fixed-size chunks,
    because related information is already co-located and linked.
    """
    if not _OPENKB_DIR.exists():
        return [
            {
                "page": "ERROR",
                "content": (
                    f"OpenKB wiki not found at {_OPENKB_DIR}. "
                    "Run `openkb compile` from the repo root first."
                ),
            }
        ]

    index_path = _OPENKB_DIR / "index.md"
    if not index_path.exists():
        return [
            {
                "page": "ERROR",
                "content": "wiki/index.md missing. The wiki may not be compiled yet.",
            }
        ]

    index_text = index_path.read_text(encoding="utf-8")

    keywords = [w for w in question.lower().split() if len(w) > 3]
    if not keywords:
        keywords = question.lower().split()

    wikilink = re.compile(r"\[\[([^\]]+)\]\]")

    candidates: list[Path] = []
    for m in wikilink.finditer(index_text):
        rel = m.group(1)
        p = _OPENKB_DIR / (rel if rel.endswith(".md") else rel + ".md")
        if p.exists():
            candidates.append(p)

    summaries_dir = _OPENKB_DIR / "summaries"
    if summaries_dir.exists():
        for p in sorted(summaries_dir.glob("*.md")):
            if p not in candidates:
                candidates.append(p)

    scored: list[tuple[int, Path, str]] = []
    for page_path in candidates:
        try:
            content = _strip_frontmatter(page_path.read_text(encoding="utf-8"))
        except OSError:
            continue
        score = _keyword_score(content, keywords)
        scored.append((score, page_path, content))

    scored.sort(key=lambda t: t[0], reverse=True)
    top5 = scored[:5]

    seen: set[Path] = {t[1] for t in top5}
    expansion: list[tuple[int, Path, str]] = []
    for _, page_path, content in top5:
        for m in wikilink.finditer(content):
            rel = m.group(1)
            linked = _OPENKB_DIR / (rel if rel.endswith(".md") else rel + ".md")
            if linked.exists() and linked not in seen:
                seen.add(linked)
                try:
                    linked_content = _strip_frontmatter(
                        linked.read_text(encoding="utf-8")
                    )
                    expansion.append(
                        (
                            _keyword_score(linked_content, keywords),
                            linked,
                            linked_content,
                        )
                    )
                except OSError:
                    continue

    expansion.sort(key=lambda t: t[0], reverse=True)
    combined = top5 + expansion[:3]

    if not combined:
        return [
            {
                "page": "index",
                "content": "No matching pages found.\n\n" + index_text,
            }
        ]

    return [
        {
            "page": str(p.relative_to(_OPENKB_DIR)).replace(".md", ""),
            "relevance_score": str(score),
            "content": content,
        }
        for score, p, content in combined
    ]


@mcp.tool()
def query_openkb_wiki(question: str) -> dict[str, Any]:
    """
    Query the OpenKB-compiled knowledge base.

    Uses tree-based retrieval: starts at index.md, scores all summary pages
    against the question, then expands into linked concept and entity pages.
    Returns up to eight pages ranked by keyword relevance.
    """
    return {
        "question": question,
        "source": "openkb_compiled_wiki",
        "retrieval_strategy": "tree_based",
        "results": _run_tree_retrieval(question),
    }


@mcp.tool()
def read_internal_wiki(topic: str) -> dict[str, Any]:
    """
    Read a page from the flat-text internal wiki.

    Tries an exact filename match (fixtures/wiki/<topic>.txt) first,
    then falls back to a case-insensitive substring match across all .txt files.
    If nothing matches, returns an error and lists the available topics.

    This is the naive baseline kept for Week 7 benchmarking.
    """
    if not _WIKI_DIR.exists():
        return {
            "error": (
                f"Wiki directory not found at {_WIKI_DIR}. "
                "Run `python scripts/seed_fixtures.py` first."
            )
        }

    pages = list(_WIKI_DIR.glob("*.txt"))
    if not pages:
        return {"error": "No wiki pages found. Run seed_fixtures.py first."}

    exact = _WIKI_DIR / f"{topic}.txt"
    if exact.exists():
        return {
            "topic": topic,
            "source": "internal_wiki_flat",
            "content": exact.read_text(encoding="utf-8"),
        }

    matches = [p for p in pages if topic.lower() in p.stem.lower()]
    if matches:
        page = matches[0]
        return {
            "topic": topic,
            "matched_file": page.name,
            "source": "internal_wiki_flat",
            "content": page.read_text(encoding="utf-8"),
        }

    return {
        "error": f"No wiki page found for topic={topic!r}.",
        "available_topics": sorted(p.stem for p in pages),
    }


@mcp.tool()
def send_slack_message(channel: str, text: str) -> dict[str, Any]:
    """
    Log a message to the local Slack message log.

    Appends one line to fixtures/messages.log in the format:
        [<ISO timestamp>] channel=<channel> | <text>

    Nothing is sent over the network. The log file is what the Week 6
    evaluation harness reads when checking whether the agent sent a message.
    """
    _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(tz=timezone.utc).isoformat()
    entry = f"[{timestamp}] channel={channel!r} | {text}\n"

    with _LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(entry)

    return {
        "status": "logged",
        "channel": channel,
        "timestamp": timestamp,
        "log_path": str(_LOG_PATH),
    }


if __name__ == "__main__":
    mcp.run()
