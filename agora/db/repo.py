"""SQLite access helpers for Ágora."""

from __future__ import annotations

import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

from agora.config import db_path, load_agora_config
from agora.db.schema import SCHEMA_SQL

_DEFAULT_CHANNELS = [
    {
        "slug": "praca",
        "name": "Praça",
        "description": "Conversa geral entre agentes e humanos.",
    },
    {
        "slug": "planejamento",
        "name": "Planejamento",
        "description": "Discussões sobre próximos passos e estratégia.",
    },
    {
        "slug": "decisoes",
        "name": "Decisões",
        "description": "Propostas e decisões formais.",
    },
    {
        "slug": "incidentes",
        "name": "Incidentes",
        "description": "Bloqueios, erros e ações de recuperação.",
    },
]

_db_init_path: Optional[Path] = None


def resolve_db_path() -> Path:
    return db_path()


def init_db(path: Optional[Path] = None) -> Path:
    """Create schema + seed default channels. Idempotent per resolved path."""
    global _db_init_path
    target = (path or resolve_db_path()).resolve()
    if _db_init_path == target and target.exists():
        return target

    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target))
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.executescript(SCHEMA_SQL)
        # usage tables (Phase 3 schema early so migrations are no-ops later)
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS agora_usage_events (
              id                INTEGER PRIMARY KEY AUTOINCREMENT,
              profile           TEXT NOT NULL,
              squad             TEXT,
              session_id        TEXT,
              task_id           TEXT,
              run_id            INTEGER,
              model             TEXT NOT NULL,
              provider          TEXT NOT NULL DEFAULT '',
              billing_mode      TEXT NOT NULL DEFAULT '',
              api_call_count    INTEGER NOT NULL DEFAULT 0,
              input_tokens      INTEGER NOT NULL DEFAULT 0,
              output_tokens     INTEGER NOT NULL DEFAULT 0,
              cache_read_tokens INTEGER NOT NULL DEFAULT 0,
              cache_write_tokens INTEGER NOT NULL DEFAULT 0,
              reasoning_tokens  INTEGER NOT NULL DEFAULT 0,
              cost_micro_usd    INTEGER NOT NULL DEFAULT 0,
              cost_status       TEXT NOT NULL DEFAULT 'unknown',
              pricing_version   TEXT,
              observed_at       INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS ix_agora_usage_profile_time
              ON agora_usage_events(profile, observed_at);
            CREATE INDEX IF NOT EXISTS ix_agora_usage_task
              ON agora_usage_events(task_id);

            CREATE TABLE IF NOT EXISTS agora_usage_rollup (
              bucket         TEXT NOT NULL,
              bucket_start   INTEGER NOT NULL,
              profile        TEXT NOT NULL,
              squad          TEXT NOT NULL DEFAULT '',
              model          TEXT NOT NULL,
              api_call_count INTEGER NOT NULL DEFAULT 0,
              total_tokens   INTEGER NOT NULL DEFAULT 0,
              cost_micro_usd INTEGER NOT NULL DEFAULT 0,
              PRIMARY KEY (bucket, bucket_start, profile, squad, model)
            );
            """
        )
        cfg = load_agora_config()
        channels = cfg.get("default_channels") or _DEFAULT_CHANNELS
        now = int(time.time())
        for ch in channels:
            if not isinstance(ch, dict):
                continue
            slug = str(ch.get("slug") or "").strip()
            name = str(ch.get("name") or slug).strip()
            if not slug or not name:
                continue
            conn.execute(
                "INSERT OR IGNORE INTO agora_channels (slug, name, description, created_at) "
                "VALUES (?, ?, ?, ?)",
                (slug, name, str(ch.get("description") or ""), now),
            )
        conn.commit()
    finally:
        conn.close()
    _db_init_path = target
    return target


@contextmanager
def connect(path: Optional[Path] = None) -> Generator[sqlite3.Connection, None, None]:
    target = init_db(path)
    conn = sqlite3.connect(str(target), timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=5000")
    try:
        yield conn
    finally:
        conn.close()
