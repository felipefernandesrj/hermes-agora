"""Squad selection helpers."""

from __future__ import annotations

from typing import Any

from agora.config import load_agora_config


def list_squads() -> dict[str, Any]:
    cfg = load_agora_config()
    return {
        "active_squad": cfg.get("active_squad"),
        "min_context_window": cfg.get("min_context_window"),
        "squads": cfg.get("squads") or {},
        "roster": cfg.get("roster") or {},
    }


def show_squad(name: str) -> dict[str, Any]:
    cfg = load_agora_config()
    squads = cfg.get("squads") or {}
    key = (name or "").strip().lower()
    if key not in squads:
        raise KeyError(f"unknown squad: {name}")
    return {"name": key, "roles": squads[key], "active": cfg.get("active_squad") == key}
