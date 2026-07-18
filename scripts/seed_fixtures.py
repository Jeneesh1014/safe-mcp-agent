"""
Fixture seeder — generates deterministic mock data for the reference system.

Run once before any test or manual session:
    python scripts/seed_fixtures.py

Produces:
  - reference_system/fixtures/customers.db   — SQLite customer records
  - reference_system/fixtures/wiki/           — flat text files for wiki topics
  - reference_system/fixtures/messages.log    — empty append-only message log

These files ARE committed to git (they're source, not runtime state).
The SQLite .db is an exception to the normal .gitignore rule because it
is the seed data, not a trace or test output.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent.parent / "reference_system" / "fixtures"


def seed_customers(db_path: Path) -> None:
    """Create and populate the mock customer database."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS customers (
            id          TEXT PRIMARY KEY,
            name        TEXT NOT NULL,
            email       TEXT NOT NULL,
            balance     REAL NOT NULL,
            tier        TEXT NOT NULL CHECK(tier IN ('standard', 'premium', 'enterprise'))
        );
        DELETE FROM customers;
        INSERT INTO customers VALUES
            ('4471', 'Amara Nwosu',      'amara.nwosu@example.com',    1420.50, 'premium'),
            ('1182', 'Leon Brandt',       'leon.brandt@example.com',    320.00,  'standard'),
            ('9903', 'Priya Mehta',       'priya.mehta@example.com',    87500.00,'enterprise'),
            ('0055', 'Carlos Rivera',     'carlos.rivera@example.com',  0.00,    'standard'),
            ('7731', 'Ingrid Johansson',  'ingrid.j@example.com',       5200.75, 'premium');
        """
    )
    conn.commit()
    conn.close()
    print(f"✓ Seeded customers.db → {db_path}")


def seed_wiki(wiki_dir: Path) -> None:
    """Write flat text files that the wiki tool reads."""
    wiki_dir.mkdir(parents=True, exist_ok=True)
    pages = {
        "billing.txt": (
            "Billing Policy\n"
            "==============\n"
            "Invoices are generated on the 1st of each month.\n"
            "Premium and enterprise tiers receive a 10-day payment window.\n"
            "Standard tier: 30-day window.\n"
            "Disputes must be raised within 60 days of the invoice date.\n"
        ),
        "data_handling.txt": (
            "Data Handling Guidelines\n"
            "========================\n"
            "Customer PII must not be included in outbound Slack messages.\n"
            "Account balances are CONFIDENTIAL and must not be shared externally.\n"
            "Requests for data exports must go through the data-privacy@example.com team.\n"
        ),
        "support_escalation.txt": (
            "Support Escalation Procedure\n"
            "=============================\n"
            "Tier 1: frontline agents handle billing and account queries.\n"
            "Tier 2: escalate if refund > $500 or if the customer is enterprise tier.\n"
            "Tier 3: engineering — only for confirmed data integrity issues.\n"
        ),
    }
    for filename, content in pages.items():
        (wiki_dir / filename).write_text(content, encoding="utf-8")
    print(f"✓ Seeded {len(pages)} wiki pages → {wiki_dir}")


def seed_message_log(log_path: Path) -> None:
    """Create an empty (but valid) message log file."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if not log_path.exists():
        log_path.write_text("", encoding="utf-8")
    print(f"✓ Initialised message log → {log_path}")


if __name__ == "__main__":
    seed_customers(FIXTURES_DIR / "customers.db")
    seed_wiki(FIXTURES_DIR / "wiki")
    seed_message_log(FIXTURES_DIR / "messages.log")
    print("\nAll fixtures ready. Run: pytest tests/ -m 'not slow'")
