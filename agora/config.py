"""Ágora configuration helpers.

Reads optional ``plugins.agora`` (or top-level ``agora``) from the active
Hermes ``config.yaml``. No profile names are hardcoded in public defaults
beyond a soft roster template the operator can override.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Optional

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None

try:
    from hermes_constants import get_hermes_home, get_default_hermes_root
except Exception:  # pragma: no cover
    def get_hermes_home() -> Path:  # type: ignore
        return Path.home() / ".hermes"

    def get_default_hermes_root() -> Path:  # type: ignore
        return Path.home() / ".hermes"


DEFAULT_ROSTER = {
    "techlead": "agent-techlead",
    "backend": "agent-backend",
    "frontend": "agent-frontend",
    "qa": "agent-qa",
    "po": "agent-po",
}

DEFAULT_AGORA_CONFIG: dict[str, Any] = {
    "roster": deepcopy(DEFAULT_ROSTER),
    "active_squad": "bravo",
    "min_context_window": 200_000,
    "completion_notify_channel": "planejamento",
    "handoff_notify_channel": "praca",
    "default_channels": [
        {"slug": "praca", "name": "Praça", "description": "Conversa geral entre agentes e humanos."},
        {"slug": "planejamento", "name": "Planejamento", "description": "Discussões sobre próximos passos e estratégia."},
        {"slug": "decisoes", "name": "Decisões", "description": "Propostas e decisões formais."},
        {"slug": "incidentes", "name": "Incidentes", "description": "Bloqueios, erros e ações de recuperação."},
    ],
    "cost": {
        "enabled": True,
        "collect_interval_seconds": 30,
        "currency_unit": "micro_usd",
    },
    "squads": {
        # Filled in Phase 5. Kept empty so packaging does not pin vendor models.
    },
}


def _load_yaml_config() -> dict[str, Any]:
    path = get_hermes_home() / "config.yaml"
    if yaml is None or not path.exists():
        return {}
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return raw if isinstance(raw, dict) else {}
    except Exception:
        return {}


def load_agora_config() -> dict[str, Any]:
    """Return merged Ágora config (defaults + user overrides)."""
    cfg = deepcopy(DEFAULT_AGORA_CONFIG)
    root = _load_yaml_config()
    user = {}
    plugins = root.get("plugins")
    if isinstance(plugins, dict) and isinstance(plugins.get("agora"), dict):
        user = plugins["agora"]
    elif isinstance(root.get("agora"), dict):
        user = root["agora"]
    # shallow+one-level merge for known sections
    for key, value in user.items():
        if isinstance(value, dict) and isinstance(cfg.get(key), dict):
            merged = dict(cfg[key])
            merged.update(value)
            cfg[key] = merged
        else:
            cfg[key] = value
    return cfg


def roster_profiles(cfg: Optional[dict[str, Any]] = None) -> list[str]:
    cfg = cfg or load_agora_config()
    roster = cfg.get("roster") or {}
    if not isinstance(roster, dict):
        return []
    out = []
    for v in roster.values():
        name = str(v or "").strip()
        if name:
            out.append(name)
    return out


def db_path() -> Path:
    return get_default_hermes_root() / "agora.db"
