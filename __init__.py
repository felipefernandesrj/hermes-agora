"""Ágora — Hermes plugin (dashboard + kanban hooks).

Installed as ``~/.hermes/plugins/agora`` (or via symlink). Dashboard
discovery reads ``dashboard/manifest.json``; agent/plugin discovery calls
``register(ctx)`` here so Kanban lifecycle hooks keep working.
"""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)


def register(ctx) -> None:
    """Register Kanban lifecycle hooks with the Hermes plugin runtime."""
    try:
        from dashboard.plugin_api import register as register_dashboard_hooks

        register_dashboard_hooks(ctx)
    except Exception:
        log.exception("Ágora: failed to register dashboard/kanban hooks")
