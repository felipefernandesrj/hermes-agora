"""PO board health watcher."""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Any, Optional

try:
    from hermes_constants import get_default_hermes_root
except Exception:  # pragma: no cover
    def get_default_hermes_root() -> Path:  # type: ignore
        return Path.home() / ".hermes"


def _kanban_db(board: str = "agora") -> Path:
    return get_default_hermes_root() / "kanban" / "boards" / board / "kanban.db"


def inspect_board(board: str = "agora", *, stale_seconds: int = 900) -> dict[str, Any]:
    path = _kanban_db(board)
    if not path.exists():
        return {"ok": False, "reason": "kanban-db-missing", "path": str(path)}

    now = int(time.time())
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    try:
        by_status = {
            r["status"]: r["n"]
            for r in conn.execute(
                "SELECT status, COUNT(*) AS n FROM tasks GROUP BY status"
            )
        }
        blocked = [
            dict(r)
            for r in conn.execute(
                "SELECT id, title, assignee, status FROM tasks WHERE status='blocked' ORDER BY created_at DESC LIMIT 20"
            )
        ]
        running = [
            dict(r)
            for r in conn.execute(
                """
                SELECT t.id, t.title, t.assignee, r.worker_pid, r.last_heartbeat_at, r.started_at, r.id AS run_id
                FROM tasks t
                LEFT JOIN task_runs r ON r.id = t.current_run_id
                WHERE t.status='running'
                ORDER BY t.created_at DESC
                LIMIT 30
                """
            )
        ]
        stale_runs = []
        for r in running:
            hb = r.get("last_heartbeat_at") or r.get("started_at") or 0
            try:
                hb_i = int(hb)
            except Exception:
                hb_i = 0
            if hb_i and (now - hb_i) > stale_seconds:
                stale_runs.append(r)
            elif r.get("worker_pid") in (None, 0) and r.get("started_at"):
                # running without pid is also a smell
                if (now - int(r.get("started_at") or now)) > stale_seconds:
                    stale_runs.append(r)
        ready = [
            dict(r)
            for r in conn.execute(
                "SELECT id, title, assignee FROM tasks WHERE status='ready' ORDER BY priority, created_at LIMIT 20"
            )
        ]
    finally:
        conn.close()

    issues = []
    if blocked:
        issues.append(f"{len(blocked)} blocked")
    if stale_runs:
        issues.append(f"{len(stale_runs)} running stale/no-heartbeat")
    healthy = not issues

    lines = [f"[PO WATCH] board={board} healthy={healthy}"]
    if issues:
        lines.append("Gargalos: " + ", ".join(issues))
        lines.append("@agent-techlead PO pede desbloqueio/orquestração dos itens abaixo.")
    for b in blocked[:8]:
        who = b.get("assignee") or "unassigned"
        mention = who if str(who).startswith("agent-") else who
        lines.append(
            f"- BLOCKED {b.get('id')} @{mention}: {b.get('title')} "
            f"(PO: iluminar; techlead: desbloquear)"
        )
    for s in stale_runs[:8]:
        who = s.get("assignee") or "unassigned"
        mention = who if str(who).startswith("agent-") else who
        lines.append(
            f"- STALE {s.get('id')} @{mention} pid={s.get('worker_pid')} "
            f"hb={s.get('last_heartbeat_at')}: {s.get('title')}"
        )
    if healthy:
        lines.append("Board saudável — sem ação.")

    return {
        "ok": True,
        "board": board,
        "healthy": healthy,
        "by_status": by_status,
        "blocked": blocked,
        "stale_runs": stale_runs,
        "ready": ready,
        "report": "\n".join(lines),
        "observed_at": now,
    }
