"""Mailbox hygiene + unread processing helpers."""

from __future__ import annotations

import sqlite3
import time
from typing import Any, Iterable, Optional

from agora.config import load_agora_config, roster_profiles

# Handles that must never become notification recipients.
_BLOCKED_HANDLES = frozenset(
    {
        "all",
        "todos",
        "everyone",
        "here",
        "channel",
        "perfil",
        "fallback",
        "mention",
        "mentions",
        "tokens",
        "token",
        "agent",
        "agents",
        "human",
        "system",
        "kanban",
        "test-helper",
        "test",
        "todo",
        "po",
        "qa",
        "backend",
        "frontend",
        "techlead",
        "tech-lead",
    }
)


def roster_set(cfg: Optional[dict[str, Any]] = None) -> set[str]:
    cfg = cfg or load_agora_config()
    return {p for p in roster_profiles(cfg)}


def is_valid_recipient(handle: str, valid: Iterable[str]) -> bool:
    h = (handle or "").strip()
    if not h:
        return False
    low = h.lower()
    if low in _BLOCKED_HANDLES:
        return False
    # role aliases not allowed unless they match an actual profile name
    valid_l = {v.lower(): v for v in valid}
    return low in valid_l


def normalize_recipient(handle: str, valid: Iterable[str]) -> Optional[str]:
    valid_l = {v.lower(): v for v in valid}
    low = (handle or "").strip().lower()
    if low in _BLOCKED_HANDLES:
        return None
    return valid_l.get(low)


def cleanup_invalid_notifications(conn: sqlite3.Connection) -> dict[str, Any]:
    """Delete notifications whose recipient is outside roster/known profiles."""
    cfg = load_agora_config()
    valid = roster_set(cfg)
    # keep existing agent_status profiles too
    try:
        rows = conn.execute("SELECT DISTINCT profile FROM agora_agent_status").fetchall()
        for r in rows:
            if r[0]:
                valid.add(r[0])
    except Exception:
        pass

    rows = conn.execute(
        "SELECT id, recipient FROM agora_notifications"
    ).fetchall()
    deleted = 0
    kept = 0
    for r in rows:
        rid = r["id"] if isinstance(r, sqlite3.Row) else r[0]
        recip = r["recipient"] if isinstance(r, sqlite3.Row) else r[1]
        if is_valid_recipient(str(recip), valid):
            kept += 1
            continue
        conn.execute("DELETE FROM agora_notifications WHERE id = ?", (rid,))
        deleted += 1
    conn.commit()
    return {"deleted": deleted, "kept": kept, "valid_roster": sorted(valid)}


def list_unread(
    conn: sqlite3.Connection,
    recipient: str,
    *,
    limit: int = 50,
) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT id, recipient, message_id, channel_id, body_snippet, author_profile,
               read_at, ack_at, created_at
        FROM agora_notifications
        WHERE recipient = ? AND read_at IS NULL
        ORDER BY created_at ASC
        LIMIT ?
        """,
        (recipient, int(limit)),
    ).fetchall()
    out = []
    for r in rows:
        out.append({k: r[k] for k in r.keys()} if isinstance(r, sqlite3.Row) else dict(r))
    return out


def mark_notification_read(conn: sqlite3.Connection, notification_id: int) -> bool:
    now = int(time.time())
    cur = conn.execute(
        "UPDATE agora_notifications SET read_at = COALESCE(read_at, ?) WHERE id = ?",
        (now, int(notification_id)),
    )
    conn.commit()
    return cur.rowcount > 0


def build_mailbox_action_brief(recipient: str, unread: list[dict[str, Any]]) -> str:
    """Text the agent should process on wake (to be posted/sent into runtime)."""
    if not unread:
        return f"Mailbox vazia para {recipient}."
    lines = [
        f"[ÁGORA MAILBOX] {recipient}: {len(unread)} notification(s) unread.",
        "Processe em ordem. Para cada item: (1) ack na #praca se necessário,",
        "(2) transforme em ação (claim card, responder menção, pedir opinião),",
        "(3) só então idle.",
        "",
    ]
    for n in unread[:20]:
        lines.append(
            f"- notif#{n.get('id')} from={n.get('author_profile')} "
            f"msg={n.get('message_id')} :: {n.get('body_snippet')}"
        )
    return "\n".join(lines)
