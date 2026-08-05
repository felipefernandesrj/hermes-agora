#!/usr/bin/env python3
"""Squad inspector/switcher/applier for Ágora.

Usage:
  python scripts/agora_squad.py list
  python scripts/agora_squad.py show bravo
  python scripts/agora_squad.py use bravo       # sets active_squad in config.yaml
  python scripts/agora_squad.py apply bravo     # writes model+provider+context_length to each profile
  python scripts/agora_squad.py check bravo     # validates min_context_window guard

Phase 5: BRAVO default, min_context_window 200k, glm-4.7-flash retired from executors.
"""

from __future__ import annotations

import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import yaml
from agora.squads import list_squads, show_squad, check_min_context_window, DEFAULT_CONTEXT_LENGTHS
from agora.config import load_agora_config

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


def cmd_apply(name: str) -> None:
    data = list_squads()
    key = name.strip().lower()
    roles = (data.get("squads") or {}).get(key)
    roster = data.get("roster") or {}
    if not isinstance(roles, dict):
        raise SystemExit(f"unknown squad: {name}")
    # map role -> profile
    stamp = time.strftime("%Y%m%d%H%M%S")
    home = get_hermes_home()
    for role, spec in roles.items():
        profile = roster.get(role)
        if not profile or not isinstance(spec, dict):
            continue
        path = home / "profiles" / str(profile) / "config.yaml"
        if not path.exists():
            print(f"skip missing profile config: {profile}")
            continue
        bak = path.with_suffix(f".yaml.bak-squad-{key}-{stamp}")
        shutil.copy2(path, bak)
        cfg = yaml.safe_load(path.read_text()) or {}
        model = {
            "default": spec.get("model"),
            "provider": spec.get("provider"),
            "max_tokens": int(spec.get("max_tokens") or 32000),
            "context_length": int(spec.get("context_length") or 1_000_000),
        }
        cfg["model"] = model
        path.write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True))
        print(f"applied {key}/{role} -> {profile}: {model['provider']} / {model['default']} (bak {bak.name})")
    cmd_use(key)
    print("NOTE: default Hermes profile was not modified.")


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
    elif cmd == "apply":
        cmd_apply(argv[1])
    else:
        raise SystemExit(f"unknown command: {cmd}")


if __name__ == "__main__":
    main(sys.argv[1:])
