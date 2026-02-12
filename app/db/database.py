from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator, Optional

from app.advisory.models import ClauseAdvisory
from app.intake.models import ValidatedDeal
from app.routing.engine import RoutingDecision
from app.rules.engine import EvaluationResult

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "gtm.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS deals (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    deal_type TEXT NOT NULL,
    customer_segment TEXT NOT NULL,
    annual_contract_value REAL NOT NULL,
    discount_percentage REAL NOT NULL,
    payment_terms_days INTEGER NOT NULL,
    region TEXT NOT NULL,
    custom_security_clause INTEGER NOT NULL,
    clause_text TEXT,
    decision_json TEXT,
    evaluation_json TEXT,
    advisory_json TEXT,
    status TEXT NOT NULL DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS overrides (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    deal_id TEXT NOT NULL REFERENCES deals(id),
    override_reason TEXT NOT NULL,
    override_notes TEXT,
    overridden_by TEXT NOT NULL DEFAULT 'approver',
    created_at TEXT NOT NULL,
    original_decision_json TEXT NOT NULL
);
"""


def _db_path() -> Path:
    env = os.environ.get("GTM_DB_PATH")
    if env:
        return Path(env)
    return DEFAULT_DB_PATH


@contextmanager
def get_conn(db_path: Path | None = None) -> Generator[sqlite3.Connection, None, None]:
    path = db_path or _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: Path | None = None) -> None:
    with get_conn(db_path) as conn:
        conn.executescript(SCHEMA)


# ---------------------------------------------------------------------------
# Deal CRUD
# ---------------------------------------------------------------------------


def insert_deal(deal: ValidatedDeal, db_path: Path | None = None) -> None:
    with get_conn(db_path) as conn:
        conn.execute(
            """INSERT INTO deals
               (id, created_at, deal_type, customer_segment, annual_contract_value,
                discount_percentage, payment_terms_days, region,
                custom_security_clause, clause_text, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'validated')""",
            (
                deal.id,
                deal.created_at.isoformat(),
                deal.deal_type.value,
                deal.customer_segment.value,
                deal.annual_contract_value,
                deal.discount_percentage,
                deal.payment_terms_days,
                deal.region.value,
                int(deal.custom_security_clause),
                deal.clause_text,
            ),
        )


def update_deal_decision(
    deal_id: str,
    evaluation: EvaluationResult,
    decision: RoutingDecision,
    advisory: ClauseAdvisory | None = None,
    db_path: Path | None = None,
) -> None:
    with get_conn(db_path) as conn:
        conn.execute(
            """UPDATE deals
               SET evaluation_json = ?, decision_json = ?, advisory_json = ?, status = 'processed'
               WHERE id = ?""",
            (
                evaluation.model_dump_json(),
                decision.model_dump_json(),
                advisory.model_dump_json() if advisory else None,
                deal_id,
            ),
        )


def get_deal(deal_id: str, db_path: Path | None = None) -> dict[str, Any] | None:
    with get_conn(db_path) as conn:
        row = conn.execute("SELECT * FROM deals WHERE id = ?", (deal_id,)).fetchone()
        if row is None:
            return None
        return _row_to_deal_dict(row)


def get_all_deals(db_path: Path | None = None) -> list[dict[str, Any]]:
    with get_conn(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM deals ORDER BY created_at DESC"
        ).fetchall()
        return [_row_to_deal_dict(r) for r in rows]


def get_processed_deals(db_path: Path | None = None) -> list[dict[str, Any]]:
    with get_conn(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM deals WHERE status = 'processed' ORDER BY created_at DESC"
        ).fetchall()
        return [_row_to_deal_dict(r) for r in rows]


def _row_to_deal_dict(row: sqlite3.Row) -> dict[str, Any]:
    d = dict(row)
    d["custom_security_clause"] = bool(d["custom_security_clause"])
    for json_field in ("decision_json", "evaluation_json", "advisory_json"):
        if d.get(json_field):
            d[json_field] = json.loads(d[json_field])
    return d


def count_deals(db_path: Path | None = None) -> int:
    with get_conn(db_path) as conn:
        return conn.execute("SELECT COUNT(*) FROM deals").fetchone()[0]


# ---------------------------------------------------------------------------
# Override CRUD
# ---------------------------------------------------------------------------


def insert_override(
    deal_id: str,
    override_reason: str,
    override_notes: str | None,
    original_decision_json: str,
    overridden_by: str = "approver",
    db_path: Path | None = None,
) -> int:
    with get_conn(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO overrides
               (deal_id, override_reason, override_notes, overridden_by,
                created_at, original_decision_json)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                deal_id,
                override_reason,
                override_notes,
                overridden_by,
                datetime.now(timezone.utc).isoformat(),
                original_decision_json,
            ),
        )
        # Update deal status
        conn.execute(
            "UPDATE deals SET status = 'overridden' WHERE id = ?", (deal_id,)
        )
        return cursor.lastrowid  # type: ignore[return-value]


def get_overrides(db_path: Path | None = None) -> list[dict[str, Any]]:
    with get_conn(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM overrides ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def get_overrides_for_deal(
    deal_id: str, db_path: Path | None = None
) -> list[dict[str, Any]]:
    with get_conn(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM overrides WHERE deal_id = ? ORDER BY created_at DESC",
            (deal_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def count_overrides(db_path: Path | None = None) -> int:
    with get_conn(db_path) as conn:
        return conn.execute("SELECT COUNT(*) FROM overrides").fetchone()[0]


# ---------------------------------------------------------------------------
# Reset
# ---------------------------------------------------------------------------


def reset_db(db_path: Path | None = None) -> None:
    with get_conn(db_path) as conn:
        conn.execute("DELETE FROM overrides")
        conn.execute("DELETE FROM deals")
