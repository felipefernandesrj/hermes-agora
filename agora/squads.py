"""Squad selection helpers with min_context_window guard.

Real BRAVO squad config for Cloudflare Workers AI models:
- Only models with context_window >= min_context_window (200k) qualify.
- glm-4.7-flash (131k) is retired from executor roles.
"""

from __future__ import annotations

from typing import Any

from agora.config import load_agora_config

# Known context windows for Cloudflare Workers AI models.
# Sourced from the CF API /models/search endpoint (verified 2026-08-04).
# Only models with >= 200k context are listed here.
DEFAULT_CONTEXT_LENGTHS: dict[str, int] = {
    "@cf/zai-org/glm-5.2": 262_144,
    "@cf/moonshotai/kimi-k2.7-code": 262_144,
    "@cf/nvidia/nemotron-3-120b-a12b": 256_000,
    "@cf/google/gemma-4-26b-a4b-it": 256_000,
    # Below 200k — listed for the guard to reject with a clear message:
    "@cf/zai-org/glm-4.7-flash": 131_072,
    "@cf/openai/gpt-oss-120b": 128_000,
    "@cf/mistralai/mistral-small-3.1-24b-instruct": 128_000,
    "@cf/meta/llama-3.3-70b-instruct-fp8-fast": 24_000,
    "@cf/qwen/qwen3-30b-a3b-fp8": 32_768,
    "@cf/meta/llama-4-scout-17b-16e-instruct": 131_000,
    "@cf/qwen/qwen2.5-coder-32b-instruct": 32_768,
    "@cf/meta/llama-3.1-8b-instruct-fp8": 16_000,
    "@cf/google/gemma-2b-it-lora": 8_000,
    "@cf/meta/llama-3.2-3b-instruct": 16_000,
    "@cf/meta/llama-3.2-1b-instruct": 16_000,
}


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


def check_min_context_window(squad_name: str) -> dict[str, Any]:
    """Validate that all models in a squad meet min_context_window.

    Returns a dict with:
      - ok: bool
      - violations: list of {role, model, context_window, min_required}
    """
    cfg = load_agora_config()
    squads = cfg.get("squads") or {}
    key = (squad_name or "").strip().lower()
    squad = squads.get(key)
    if not squad:
        return {"ok": False, "violations": [], "error": f"unknown squad: {squad_name}"}

    min_ctx = cfg.get("min_context_window", 200_000)
    violations = []
    for role, spec in squad.items():
        model = spec.get("model", "") if isinstance(spec, dict) else ""
        ctx = DEFAULT_CONTEXT_LENGTHS.get(model)
        if ctx is None:
            # Unknown model — allow but warn
            violations.append({
                "role": role,
                "model": model,
                "context_window": "unknown",
                "min_required": min_ctx,
                "warning": "unknown model context — verify manually",
            })
        elif ctx < min_ctx:
            violations.append({
                "role": role,
                "model": model,
                "context_window": ctx,
                "min_required": min_ctx,
            })

    return {"ok": len(violations) == 0, "violations": violations}
