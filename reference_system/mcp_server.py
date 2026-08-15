"""
MCP server — exposes four mock enterprise tools.

Tools (Week 2):
  - query_customer_db(customer_id)   reads from the seeded SQLite DB
  - query_openkb_wiki(question)      tree-based retrieval from OpenKB wiki/
  - read_internal_wiki(topic)        flat-text fallback reader (fixtures/wiki/)
  - send_slack_message(channel, text) appends to a local log file

No security validation lives here intentionally. That is the middleware's job
(Week 5). Week 2 target: all four tools callable, returning realistic-looking
mock data.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Paths — relative to this file so the server works regardless of cwd
# ---------------------------------------------------------------------------

_HERE = Path(__file__).parent
_FIXTURES = _HERE / "fixtures"
_DB_PATH = _FIXTURES / "customers.db"
_WIKI_DIR = _FIXTURES / "wiki"
_LOG_PATH = _FIXTURES / "messages.log"

# OpenKB compiled wiki lives at the repo root (gitignored, built in Week 1)
_OPENKB_DIR = _HERE.parent / "wiki"

# ---------------------------------------------------------------------------
# Pydantic input schemas — one per tool
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# MCP server instance
# ---------------------------------------------------------------------------

mcp = FastMCP("safe-mcp-agent")

# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


@mcp.tool()
def query_customer_db(customer_id: str) -> dict[str, Any]:
    """
    Look up a customer record by customer_id.

    Returns a dictionary with fields: id, name, email, balance, tier.
    Returns an error dict if the customer is not found or the DB is missing.
    """
    if not _DB_PATH.exists():
        return {
            "error": f"Customer database not found at {_DB_PATH}. "
            "Run `python scripts/seed_fixtures.py` first."
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


# ---------------------------------------------------------------------------


def _load_wiki_page(path: Path) -> str:
    """Read a markdown page from the OpenKB wiki, stripping YAML frontmatter."""
    text = path.read_text(encoding="utf-8")
    # Strip leading YAML frontmatter (--- ... ---)
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            text = text[end + 3 :].lstrip("\n")
    return text


def _score_page(text: str, keywords: list[str]) -> int:
    """Return a simple keyword hit count for ranking pages."""
    lower = text.lower()
    return sum(lower.count(kw.lower()) for kw in keywords)


def _openkb_tree_retrieval(question: str) -> list[dict[str, str]]:
    """
    Tree-based retrieval against the compiled OpenKB wiki.

    Strategy (mirrors how OpenKB itself navigates its knowledge graph):
      1. Parse index.md to build a map of all pages and their descriptions.
      2. Score every index entry against the question keywords.
      3. Follow the top-scoring branch: read summaries first (they reference
         concepts and entities via [[wikilinks]]). Then expand into the linked
         concept and entity pages.
      4. Return a ranked list of {page, content} dicts for the top matches.

    This is deliberately *not* blind chunking — we follow the wiki's own
    link structure rather than treating the corpus as a flat bag of text.
    """
    if not _OPENKB_DIR.exists():
        return [
            {
                "page": "ERROR",
                "content": (
                    f"OpenKB wiki directory not found at {_OPENKB_DIR}. "
                    "Run `openkb compile` from the repo root first."
                ),
            }
        ]

    index_path = _OPENKB_DIR / "index.md"
    if not index_path.exists():
        return [
            {
                "page": "ERROR",
                "content": "index.md not found in wiki/. Wiki may not be compiled.",
            }
        ]

    # Step 1 — Parse index.md to discover all pages
    index_text = index_path.read_text(encoding="utf-8")
    keywords = [w for w in question.lower().split() if len(w) > 3]
    if not keywords:
        keywords = question.lower().split()

    # Collect candidate page paths from the index
    import re

    wikilink_pattern = re.compile(r"\[\[([^\]]+)\]\]")
    candidate_paths: list[Path] = []
    for match in wikilink_pattern.finditer(index_text):
        rel = match.group(1)
        candidate = _OPENKB_DIR / (rel if rel.endswith(".md") else rel + ".md")
        if candidate.exists():
            candidate_paths.append(candidate)

    # Always include all summaries as primary retrieval targets
    summaries_dir = _OPENKB_DIR / "summaries"
    if summaries_dir.exists():
        for p in summaries_dir.glob("*.md"):
            if p not in candidate_paths:
                candidate_paths.append(p)

    # Step 2 — Score every candidate page
    scored: list[tuple[int, Path, str]] = []
    for page_path in candidate_paths:
        try:
            content = _load_wiki_page(page_path)
        except OSError:
            continue
        score = _score_page(content, keywords)
        scored.append((score, page_path, content))

    # Sort descending by score; take top candidates
    scored.sort(key=lambda t: t[0], reverse=True)
    top = scored[:5] if scored else []

    # Step 3 — Expand by following [[wikilinks]] in the top-scoring pages
    expanded_paths: set[Path] = {t[1] for t in top}
    expansion: list[tuple[int, Path, str]] = []
    for _, page_path, content in top:
        for match in wikilink_pattern.finditer(content):
            rel = match.group(1)
            linked = _OPENKB_DIR / (rel if rel.endswith(".md") else rel + ".md")
            if linked.exists() and linked not in expanded_paths:
                expanded_paths.add(linked)
                try:
                    linked_content = _load_wiki_page(linked)
                    link_score = _score_page(linked_content, keywords)
                    expansion.append((link_score, linked, linked_content))
                except OSError:
                    continue

    expansion.sort(key=lambda t: t[0], reverse=True)
    combined = top + expansion[:3]  # up to 8 pages total

    if not combined:
        return [
            {
                "page": "index",
                "content": (
                    "No pages found matching your question. "
                    "Available topics:\n" + index_text
                ),
            }
        ]

    # Step 4 — Build result list
    results: list[dict[str, str]] = []
    for score, page_path, content in combined:
        rel_name = str(page_path.relative_to(_OPENKB_DIR)).replace(".md", "")
        results.append(
            {
                "page": rel_name,
                "relevance_score": str(score),
                "content": content,
            }
        )
    return results


@mcp.tool()
def query_openkb_wiki(question: str) -> dict[str, Any]:
    """
    Query the OpenKB-compiled knowledge base using tree-based retrieval.

    Navigates the wiki's own index and wikilink graph rather than doing
    blind chunk search. Returns a list of the most relevant pages along
    with their content and a keyword-hit relevance score.
    """
    hits = _openkb_tree_retrieval(question)
    return {
        "question": question,
        "source": "openkb_compiled_wiki",
        "retrieval_strategy": "tree_based",
        "results": hits,
    }


# ---------------------------------------------------------------------------


@mcp.tool()
def read_internal_wiki(topic: str) -> dict[str, Any]:
    """
    Read a topic page from the flat-text internal wiki.

    Looks for an exact filename match first (<topic>.txt), then falls back
    to a case-insensitive substring search across all .txt files.
    Kept as a comparison point for Week 7's benchmarking against the
    OpenKB tree-based retrieval.
    """
    if not _WIKI_DIR.exists():
        return {
            "error": f"Wiki directory not found at {_WIKI_DIR}. "
            "Run `python scripts/seed_fixtures.py` first."
        }

    pages = list(_WIKI_DIR.glob("*.txt"))
    if not pages:
        return {"error": "No wiki pages found. Run seed_fixtures.py first."}

    # Exact match first
    exact = _WIKI_DIR / f"{topic}.txt"
    if exact.exists():
        return {
            "topic": topic,
            "source": "internal_wiki_flat",
            "content": exact.read_text(encoding="utf-8"),
        }

    # Case-insensitive substring match
    topic_lower = topic.lower()
    matches = [p for p in pages if topic_lower in p.stem.lower()]
    if matches:
        page = matches[0]
        return {
            "topic": topic,
            "matched_file": page.name,
            "source": "internal_wiki_flat",
            "content": page.read_text(encoding="utf-8"),
        }

    # No match — list available topics
    available = sorted(p.stem for p in pages)
    return {
        "error": f"No wiki page found for topic={topic!r}.",
        "available_topics": available,
    }


# ---------------------------------------------------------------------------


@mcp.tool()
def send_slack_message(channel: str, text: str) -> dict[str, Any]:
    """
    Append a message to the local Slack message log.

    Does NOT send anything over the network. The log lives at
    reference_system/fixtures/messages.log and is the persistent record
    used by the evaluation harness in Week 6.
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


# ---------------------------------------------------------------------------
# Entry point — run with:  python -m reference_system.mcp_server
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()
