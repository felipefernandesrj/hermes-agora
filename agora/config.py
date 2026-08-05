"""Ágora configuration helpers.

Reads optional ``plugins.agora`` (or top-level ``agora``) from the active
Hermes ``config.yaml``. No profile names are hardcoded in public defaults
beyond a soft roster template the operator can override.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None

try:
    from hermes_constants import get_default_hermes_root, get_hermes_home
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
        # BRAVO — moderate (daily default). All models >= 200k context on CF Workers AI.
        # Verified via CF API /models/search 2026-08-04.
        "bravo": {
            "techlead": {"provider": "custom:cloudflare-workers-ai", "model": "@cf/zai-org/glm-5.2", "context_window": 262144},
            "backend": {"provider": "custom:cloudflare-workers-ai", "model": "@cf/moonshotai/kimi-k2.7-code", "context_window": 262144},
            "frontend": {"provider": "custom:cloudflare-workers-ai", "model": "@cf/moonshotai/kimi-k2.7-code", "context_window": 262144},
            "qa": {"provider": "custom:cloudflare-workers-ai", "model": "@cf/nvidia/nemotron-3-120b-a12b", "context_window": 256000},
            "po": {"provider": "custom:cloudflare-workers-ai", "model": "@cf/zai-org/glm-5.2", "context_window": 262144},
        },
        # ALFA — premium (architecture, incidents). Uses GitHub Models for vendor diversity.
        "alfa": {
            "techlead": {"provider": "custom:github-models", "model": "openai/gpt-4.1", "context_window": 1048576},
            "backend": {"provider": "custom:github-models", "model": "openai/gpt-4.1", "context_window": 1048576},
            "frontend": {"provider": "custom:github-models", "model": "openai/gpt-4.1", "context_window": 1048576},
            "qa": {"provider": "custom:github-models", "model": "openai/gpt-4o", "context_window": 1048576},
            "po": {"provider": "custom:github-models", "model": "openai/gpt-4.1-mini", "context_window": 1048576},
        },
        # CHARLIE — economical (cron, triage, sweeps). Still >= 200k context.
        "charlie": {
            "techlead": {"provider": "custom:cloudflare-workers-ai", "model": "@cf/zai-org/glm-5.2", "context_window": 262144},
            "backend": {"provider": "custom:cloudflare-workers-ai", "model": "@cf/google/gemma-4-26b-a4b-it", "context_window": 256000},
            "frontend": {"provider": "custom:cloudflare-workers-ai", "model": "@cf/google/gemma-4-26b-a4b-it", "context_window": 256000},
            "qa": {"provider": "custom:cloudflare-workers-ai", "model": "@cf/nvidia/nemotron-3-120b-a12b", "context_window": 256000},
            "po": {"provider": "custom:cloudflare-workers-ai", "model": "@cf/google/gemma-4-26b-a4b-it", "context_window": 256000},
        },
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


def roster_profiles(cfg: dict[str, Any] | None = None) -> list[str]:
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
