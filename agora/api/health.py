"""Health endpoint helpers."""

from __future__ import annotations

import shutil
import time
from typing import Any

from agora.config import load_agora_config, roster_profiles
from agora.db.repo import connect, resolve_db_path


def build_health() -> dict[str, Any]:
    started = time.time()
    notes: list[str] = []
    capabilities = {
        "db": False,
        "tmux": shutil.which("tmux") is not None,
        "kanban": False,
        "roster": False,
    }
    status = "healthy"
    cfg = load_agora_config()
    roster = roster_profiles(cfg)
    capabilities["roster"] = bool(roster)
    if not roster:
        notes.append("roster empty")

    try:
        with connect() as conn:
            n = conn.execute("SELECT COUNT(*) AS c FROM agora_channels").fetchone()["c"]
            capabilities["db"] = True
            notes.append(f"channels={n}")
    except Exception as exc:
        status = "degraded"
        notes.append(f"db error: {type(exc).__name__}")

    try:
        from hermes_cli import kanban_db as _kanban_db  # type: ignore

        capabilities["kanban"] = _kanban_db is not None
    except Exception:
        capabilities["kanban"] = False
        notes.append("kanban unavailable")

    if not capabilities["tmux"]:
        notes.append("tmux optional missing")
    if not capabilities["db"]:
        status = "unhealthy"

    return {
        "status": status,
        "timestamp": int(time.time()),
        "ping_ms": int((time.time() - started) * 1000),
        "db_path": str(resolve_db_path()),
        "active_squad": cfg.get("active_squad"),
        "roster": roster,
        "capabilities": capabilities,
        "notes": notes,
    }
