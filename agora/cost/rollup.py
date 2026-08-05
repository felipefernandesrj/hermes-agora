"""Usage rollups and task correlation for Ágora cost telemetry."""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Any

from agora.db.repo import connect

try:
    from hermes_constants import get_hermes_home
except Exception:  # pragma: no cover
    def get_hermes_home() -> Path:  # type: ignore
        return Path.home() / ".hermes"


def rebuild_hour_rollups(*, since: int | None = None) -> int:
    """Rebuild hour buckets from agora_usage_events. Returns rows written."""
    if since is None:
        since = int(time.time()) - 7 * 86400
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
              (observed_at / 3600) * 3600 AS bucket_start,
              profile,
              COALESCE(squad, '') AS squad,
              model,
              SUM(api_call_count) AS api_call_count,
              SUM(input_tokens + output_tokens + cache_read_tokens + cache_write_tokens + reasoning_tokens) AS total_tokens,
              SUM(cost_micro_usd) AS cost_micro_usd
            FROM agora_usage_events
            WHERE observed_at >= ?
            GROUP BY 1, 2, 3, 4
            """,
            (since,),
        ).fetchall()
        written = 0
        for r in rows:
            conn.execute(
                """
                INSERT INTO agora_usage_rollup (
                  bucket, bucket_start, profile, squad, model,
                  api_call_count, total_tokens, cost_micro_usd
                ) VALUES ('hour', ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(bucket, bucket_start, profile, squad, model) DO UPDATE SET
                  api_call_count=excluded.api_call_count,
                  total_tokens=excluded.total_tokens,
                  cost_micro_usd=excluded.cost_micro_usd
                """,
                (
                    int(r["bucket_start"]),
                    r["profile"],
                    r["squad"],
                    r["model"],
                    int(r["api_call_count"] or 0),
                    int(r["total_tokens"] or 0),
                    int(r["cost_micro_usd"] or 0),
                ),
            )
            written += 1
        conn.commit()
        return written


def _kanban_db_path() -> Path | None:
    home = get_hermes_home()
    candidates = [
        home / "kanban" / "boards" / "agora" / "kanban.db",
        home / "kanban" / "agora.db",
        home / "kanban.db",
    ]
    for p in candidates:
        if p.exists() and p.stat().st_size > 0:
            return p
    return None


def correlate_task_ids(limit: int = 5000) -> dict[str, Any]:
    """Best-effort fill task_id/run_id on usage events via session timestamps vs task_runs.

    Heuristic: for each usage event with null task_id, find a task_run for the same
    profile whose [started_at, ended_at|now] window contains observed_at.
    """
    kpath = _kanban_db_path()
    if kpath is None:
        return {"updated": 0, "reason": "kanban-db-missing"}

    updated = 0
    with connect() as out, sqlite3.connect(str(kpath)) as kdb:
        kdb.row_factory = sqlite3.Row
        events = out.execute(
            """
            SELECT id, profile, observed_at
            FROM agora_usage_events
            WHERE task_id IS NULL
            ORDER BY id DESC
            LIMIT ?
            """,
            (int(limit),),
        ).fetchall()
        for ev in events:
            profile = ev["profile"]
            ts = int(ev["observed_at"] or 0)
            row = kdb.execute(
                """
                SELECT id AS run_id, task_id
                FROM task_runs
                WHERE profile = ?
                  AND started_at IS NOT NULL
                  AND started_at <= ?
                  AND (ended_at IS NULL OR ended_at >= ?)
                ORDER BY started_at DESC
                LIMIT 1
                """,
                (profile, ts, ts),
            ).fetchone()
            if not row:
                continue
            out.execute(
                "UPDATE agora_usage_events SET task_id = ?, run_id = ? WHERE id = ?",
                (row["task_id"], int(row["run_id"]), int(ev["id"])),
            )
            updated += 1
        out.commit()
    return {"updated": updated, "scanned": len(events)}
