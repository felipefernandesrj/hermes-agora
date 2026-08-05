"""Completion gates: handoff vault + praça evidence."""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Any, Optional

from agora.config import db_path as agora_db_path

try:
    from hermes_constants import get_default_hermes_root
except Exception:  # pragma: no cover
    def get_default_hermes_root() -> Path:  # type: ignore
        return Path.home() / ".hermes"


def vault_handoffs_dir() -> Path:
    cfg_path = get_default_hermes_root() / "config.yaml"
    vault = Path.home() / "Documents" / "Obsidian Vault"
    try:
        import yaml  # type: ignore

        raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        rr = raw.get("rag_revival") or {}
        if isinstance(rr, dict) and rr.get("vault_dir"):
            vault = Path(str(rr["vault_dir"]))
    except Exception:
        pass
    d = vault / "04 Referências" / "agora" / "handoffs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def find_handoff(task_id: str) -> Optional[Path]:
    d = vault_handoffs_dir()
    # exact and prefix matches
    exact = d / f"{task_id}.md"
    if exact.exists():
        return exact
    matches = sorted(d.glob(f"*{task_id}*.md"))
    if matches:
        return matches[0]
    # content search (handoffs may use descriptive filenames)
    needle = str(task_id)
    for path in sorted(d.glob("*.md")):
        try:
            txt = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if needle in txt:
            return path
    return None


def praca_posts_for_task(task_id: str) -> list[dict[str, Any]]:
    path = agora_db_path()
    if not path.exists():
        return []
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT m.id, m.author_profile, m.body, m.created_at, m.linked_task_id
            FROM agora_messages m
            JOIN agora_channels c ON c.id = m.channel_id
            WHERE c.slug = 'praca'
              AND (
                m.linked_task_id = ?
                OR m.body LIKE ?
              )
            ORDER BY m.id DESC
            LIMIT 50
            """,
            (task_id, f"%{task_id}%"),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def evaluate_complete_gate(task_id: str) -> dict[str, Any]:
    handoff = find_handoff(task_id)
    posts = praca_posts_for_task(task_id)
    ok = bool(handoff) and len(posts) >= 1
    missing = []
    if not handoff:
        missing.append("handoff_vault")
    if len(posts) < 1:
        missing.append("praca_post")
    return {
        "ok": ok,
        "task_id": task_id,
        "handoff_path": str(handoff) if handoff else None,
        "praca_posts": len(posts),
        "missing": missing,
        "checked_at": int(time.time()),
        "message": (
            "gate pass"
            if ok
            else "kanban_complete blocked: missing "
            + ",".join(missing)
            + f" for {task_id}. Write handoff in vault and post checkpoint on #praca."
        ),
    }
