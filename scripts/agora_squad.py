#!/usr/bin/env python3
"""Minimal squad inspector/switcher for Ágora.

Usage:
  python scripts/agora_squad.py list
  python scripts/agora_squad.py show bravo
  python scripts/agora_squad.py use bravo   # writes plugins.agora.active_squad only
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import yaml
from agora.squads import list_squads, show_squad

try:
    from hermes_constants import get_hermes_home
except Exception:
    def get_hermes_home():
        return Path.home() / ".hermes"


def _cfg_path() -> Path:
    return get_hermes_home() / "config.yaml"


def cmd_use(name: str) -> None:
    data = list_squads()
    key = name.strip().lower()
    if key not in (data.get("squads") or {}):
        raise SystemExit(f"unknown squad: {name}. known={list((data.get('squads') or {}))}")
    path = _cfg_path()
    cfg = yaml.safe_load(path.read_text()) if path.exists() else {}
    plugins = cfg.get("plugins") if isinstance(cfg.get("plugins"), dict) else {}
    agora = plugins.get("agora") if isinstance(plugins.get("agora"), dict) else {}
    agora["active_squad"] = key
    plugins["agora"] = agora
    cfg["plugins"] = plugins
    path.write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True))
    print(f"active_squad={key}")
    print("NOTE: this only records the desired squad. Applying model/provider to each profile is a separate step (Phase 5 apply).")


def main(argv: list[str]) -> None:
    if not argv or argv[0] in {"-h", "--help"}:
        print(__doc__)
        return
    cmd = argv[0]
    if cmd == "list":
        import json
        print(json.dumps(list_squads(), indent=2, ensure_ascii=False))
    elif cmd == "show":
        import json
        print(json.dumps(show_squad(argv[1]), indent=2, ensure_ascii=False))
    elif cmd == "use":
        cmd_use(argv[1])
    else:
        raise SystemExit(f"unknown command: {cmd}")


if __name__ == "__main__":
    main(sys.argv[1:])
