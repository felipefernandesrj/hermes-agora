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

from agora.config import load_agora_config
from agora.squads import DEFAULT_CONTEXT_LENGTHS, check_min_context_window, list_squads, show_squad

try:
    from hermes_constants import get_default_hermes_root, get_hermes_home
except Exception:
    def get_hermes_home():
        return Path.home() / ".hermes"

    def get_default_hermes_root():
        return Path.home() / ".hermes"


def _hermes_root() -> Path:
    """Return the base .hermes directory (not profile-scoped)."""
    return get_default_hermes_root()


def _cfg_path() -> Path:
    return _hermes_root() / "config.yaml"


def cmd_use(name: str) -> None:
    data = list_squads()
    key = name.strip().lower()
    if key not in (data.get("squads") or {}):
        raise SystemExit(f"unknown squad: {name}. known={list(data.get('squads') or {})}")
    path = _cfg_path()
    cfg = yaml.safe_load(path.read_text()) if path.exists() else {}
    plugins = cfg.get("plugins") if isinstance(cfg.get("plugins"), dict) else {}
    agora = plugins.get("agora") if isinstance(plugins.get("agora"), dict) else {}
    agora["active_squad"] = key
    plugins["agora"] = agora
    cfg["plugins"] = plugins
    path.write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True))
    print(f"active_squad={key}")


def cmd_check(name: str) -> None:
    result = check_min_context_window(name)
    if result["ok"]:
        print(f"Squad '{name}': PASS (all models >= min_context_window)")
    else:
        print(f"Squad '{name}': FAIL")
        for v in result.get("violations", []):
            print(f"  {v['role']}: {v['model']} ctx={v['context_window']} < min={v['min_required']}")
        sys.exit(1)


def cmd_apply(name: str) -> None:
    """Write model+provider+context_length to each profile config.yaml.

    Guard: refuses to apply if any model has context_window below min_context_window.
    """
    cfg = load_agora_config()
    key = name.strip().lower()
    squads = cfg.get("squads") or {}
    roster = cfg.get("roster") or {}
    if key not in squads:
        raise SystemExit(f"unknown squad: {name}. known={list(squads)}")

    squad = squads[key]

    # Guard: check min_context_window before applying
    guard = check_min_context_window(key)
    hard_violations = [v for v in guard.get("violations", []) if isinstance(v.get("context_window"), int)]
    if hard_violations:
        min_ctx = cfg.get("min_context_window", 200_000)
        print(f"REFUSED: squad '{key}' has models below min_context_window ({min_ctx}):")
        for v in hard_violations:
            print(f"  {v['role']}: {v['model']} ctx={v['context_window']} < min={v['min_required']}")
        sys.exit(1)

    min_ctx = cfg.get("min_context_window", 200_000)
    stamp = time.strftime("%Y%m%d%H%M%S")
    home = _hermes_root()

    for role, spec in squad.items():
        profile_name = roster.get(role)
        if not profile_name:
            print(f"  SKIP {role}: no profile in roster")
            continue

        path = home / "profiles" / str(profile_name) / "config.yaml"
        if not path.exists():
            print(f"  SKIP {role}: profile {profile_name} config not found at {path}")
            continue

        bak = path.with_suffix(f".yaml.bak-squad-{key}-{stamp}")
        shutil.copy2(path, bak)
        pcfg = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        model = spec.get("model", "")
        provider = spec.get("provider", "")
        ctx = spec.get("context_window", DEFAULT_CONTEXT_LENGTHS.get(model, min_ctx))

        old_model = pcfg.get("model", {}).get("default", "?") if isinstance(pcfg.get("model"), dict) else "?"
        pcfg.setdefault("model", {})["default"] = model
        pcfg["model"]["provider"] = provider
        pcfg["model"]["max_tokens"] = int(spec.get("max_tokens") or 32000)
        pcfg["model"]["context_length"] = ctx

        path.write_text(yaml.safe_dump(pcfg, sort_keys=False, allow_unicode=True), encoding="utf-8")
        print(f"  {role} ({profile_name}): {old_model} -> {model} (ctx={ctx}, bak={bak.name})")

    # Also set active_squad
    cmd_use(key)
    print(f"\nSquad '{key}' applied to {len(squad)} profiles.")
    print("Restart workers for changes to take effect.")


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
    elif cmd == "check":
        cmd_check(argv[1])
    elif cmd == "apply":
        cmd_apply(argv[1])
    else:
        raise SystemExit(f"unknown command: {cmd}")


if __name__ == "__main__":
    main(sys.argv[1:])
