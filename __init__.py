"""Ágora — Hermes plugin (dashboard + operational hooks).

Installed as ``~/.hermes/plugins/agora`` and per-profile
``profiles/<name>/plugins/agora``.

Hooks (worker + dispatcher processes):
- ``pre_tool_call`` blocks ``kanban_complete`` without handoff+#praca evidence
- ``pre_llm_call`` injects unread mailbox action brief
- ``on_session_start`` same mailbox inject for new worker sessions
- ``kanban_task_claimed`` best-effort wake note for observability
- dashboard kanban lifecycle hooks (completed/blocked/circuit)
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

log = logging.getLogger(__name__)


def _current_task_id(args: Optional[dict] = None) -> str:
    if isinstance(args, dict):
        tid = str(args.get("task_id") or "").strip()
        if tid:
            return tid
    return (os.environ.get("HERMES_KANBAN_TASK") or "").strip()


def _profile_name() -> str:
    return (
        os.environ.get("HERMES_PROFILE")
        or os.environ.get("HERMES_AGENT_PROFILE")
        or ""
    ).strip()


def _mailbox_context(profile: str) -> str:
    if not profile:
        return ""
    try:
        from agora.db.repo import connect
        from agora.ops.mailbox import build_mailbox_action_brief, list_unread

        with connect() as conn:
            unread = list_unread(conn, profile, limit=30)
        if not unread:
            return ""
        return build_mailbox_action_brief(profile, unread)
    except Exception:
        log.exception("agora mailbox context failed for %s", profile)
        return ""


def _pre_tool_call(tool_name: str = "", args: dict | None = None, **kwargs):
    if tool_name != "kanban_complete":
        return None
    tid = _current_task_id(args if isinstance(args, dict) else None)
    if not tid:
        return {
            "action": "block",
            "message": (
                "Ágora gate: kanban_complete requires task_id "
                "(or HERMES_KANBAN_TASK)."
            ),
        }
    try:
        from agora.ops.gates import evaluate_complete_gate

        gate = evaluate_complete_gate(tid)
    except Exception as exc:
        log.exception("agora complete gate failed")
        return {
            "action": "block",
            "message": f"Ágora gate error for {tid}: {type(exc).__name__}: {exc}",
        }
    if gate.get("ok"):
        return None
    missing = ", ".join(gate.get("missing") or []) or "requirements"
    return {
        "action": "block",
        "message": (
            f"Ágora gate blocked kanban_complete for {tid}. Missing: {missing}. "
            "Write vault handoff under "
            "`04 Referências/agora/handoffs/` (include task id) and post a "
            f"#praca checkpoint mentioning {tid}, then retry."
        ),
    }


def _pre_llm_call(session_id: str = "", user_message: str = "", **kwargs):
    profile = _profile_name()
    brief = _mailbox_context(profile)
    if not brief:
        return None
    # Inject into user-turn context (not system prompt) so caching stays safe.
    return {
        "context": brief
        + "\n\n(Contexto Ágora mailbox — processe unread antes de idle.)"
    }


def _on_session_start(session_id: str = "", **kwargs):
    # Same inject path via pre_llm_call on first turn; keep hook for telemetry.
    profile = _profile_name()
    if not profile:
        return None
    try:
        from agora.db.repo import connect
        from agora.ops.mailbox import list_unread

        with connect() as conn:
            n = len(list_unread(conn, profile, limit=5))
        if n:
            log.info("agora session_start profile=%s unread=%s", profile, n)
    except Exception:
        pass
    return None


def _on_kanban_task_claimed(
    task_id: str = "",
    assignee: str | None = None,
    board: str | None = None,
    **kwargs,
):
    """Dispatcher-side: leave a praça system breadcrumb when work is claimed."""
    try:
        # Lazy import dashboard helpers only when available.
        from dashboard.plugin_api import CreateMessageBody, create_channel_message

        who = assignee or "worker"
        body = (
            f"@{who} claimed `{task_id}` on board `{board or 'agora'}`. "
            "Lembrete: stream live no dashboard, checkpoint na #praca, "
            "handoff no vault antes de kanban_complete."
        )
        create_channel_message(
            "planejamento",
            CreateMessageBody(
                body=body,
                author_type="system",
                author_profile="agora",
                linked_task_id=task_id or None,
            ),
        )
    except Exception:
        log.debug("agora claim breadcrumb skipped", exc_info=True)
    return None


def register(ctx) -> None:
    """Register operational + dashboard hooks."""
    # Operational hooks (workers/dispatcher)
    try:
        ctx.register_hook("pre_tool_call", _pre_tool_call)
        ctx.register_hook("pre_llm_call", _pre_llm_call)
        ctx.register_hook("on_session_start", _on_session_start)
        ctx.register_hook("kanban_task_claimed", _on_kanban_task_claimed)
    except Exception:
        log.exception("Ágora: failed to register operational hooks")

    # Dashboard lifecycle hooks (completed/blocked/circuit) if importable
    try:
        from dashboard.plugin_api import register as register_dashboard_hooks

        register_dashboard_hooks(ctx)
    except Exception:
        log.exception("Ágora: failed to register dashboard/kanban hooks")
