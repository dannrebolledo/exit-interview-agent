"""
Storage for exit interviews and their codings.

SQLite on local disk. For a demo this beats a hosted database on every axis
that matters: nothing to keep warm, nothing that pauses after a week of
inactivity, no credentials, and the whole dataset ships with the repo so the
thing works the moment it deploys.

On Render's free tier the filesystem is ephemeral, so anything written at
runtime is lost on redeploy. That's fine here — the seeded interviews are
committed to the repo and live interviews are a bonus. If this were real you'd
point DB_PATH at a mounted disk or a managed Postgres.
"""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

DB_PATH = Path(os.getenv("DB_PATH", Path(__file__).resolve().parent.parent / "data" / "interviews.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS interviews (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id    TEXT UNIQUE,
    created_at         TEXT NOT NULL,
    site               TEXT,
    shift_pattern      TEXT,
    department         TEXT,
    tenure_months      INTEGER,
    duration_seconds   INTEGER,
    consent_given      INTEGER DEFAULT 1,
    transcript         TEXT,
    coding_json        TEXT,
    source             TEXT DEFAULT 'live'
);

CREATE INDEX IF NOT EXISTS idx_site  ON interviews(site);
CREATE INDEX IF NOT EXISTS idx_shift ON interviews(shift_pattern);
"""


@contextmanager
def conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    finally:
        c.close()


def init():
    with conn() as c:
        c.executescript(SCHEMA)


def save_interview(
    conversation_id: str,
    transcript: str,
    coding: dict,
    site: Optional[str] = None,
    shift_pattern: Optional[str] = None,
    department: Optional[str] = None,
    tenure_months: Optional[int] = None,
    duration_seconds: Optional[int] = None,
    consent_given: bool = True,
    source: str = "live",
) -> int:
    with conn() as c:
        cur = c.execute(
            """INSERT OR REPLACE INTO interviews
               (conversation_id, created_at, site, shift_pattern, department,
                tenure_months, duration_seconds, consent_given, transcript,
                coding_json, source)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                conversation_id,
                datetime.now(timezone.utc).isoformat(),
                site, shift_pattern, department, tenure_months,
                duration_seconds, int(consent_given), transcript,
                json.dumps(coding), source,
            ),
        )
        return cur.lastrowid


def all_interviews(site=None, shift=None) -> list[dict]:
    q = "SELECT * FROM interviews WHERE consent_given = 1"
    params: list = []
    if site:
        q += " AND site = ?"
        params.append(site)
    if shift:
        q += " AND shift_pattern = ?"
        params.append(shift)
    q += " ORDER BY created_at DESC"

    with conn() as c:
        rows = c.execute(q, params).fetchall()

    out = []
    for r in rows:
        d = dict(r)
        try:
            d["coding"] = json.loads(d.pop("coding_json") or "{}")
        except json.JSONDecodeError:
            d["coding"] = {}
        out.append(d)
    return out


def count() -> int:
    with conn() as c:
        return c.execute("SELECT COUNT(*) FROM interviews").fetchone()[0]
