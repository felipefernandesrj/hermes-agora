"""Micro-dollar cost helpers. Prefer Hermes usage_pricing when available."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Any

MICRO = Decimal(1000000)


def usd_to_micro(amount_usd: Any) -> int:
    if amount_usd is None:
        return 0
    try:
        d = Decimal(str(amount_usd))
    except Exception:
        return 0
    return int((d * MICRO).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def micro_to_usd_str(micro: int) -> str:
    d = (Decimal(int(micro or 0)) / MICRO).quantize(Decimal("0.000001"))
    return f"{d:.6f}"


def _candidate_routes(model: str, provider: str | None) -> list[tuple[str, str | None]]:
    """Return (model, provider) candidates for pricing lookup."""
    raw_model = (model or "").strip()
    raw_provider = (provider or "").strip() or None
    out: list[tuple[str, str | None]] = []
    seen: set[tuple[str, str | None]] = set()

    def add(m: str, p: str | None) -> None:
        key = (m, p)
        if not m or key in seen:
            return
        seen.add(key)
        out.append(key)

    add(raw_model, raw_provider)

    # Strip Cloudflare Workers AI prefix: @cf/zai-org/glm-4.7-flash
    bare = raw_model
    if bare.startswith("@cf/"):
        bare = bare[len("@cf/") :]
        add(bare, raw_provider)
        add(bare, "openrouter")
        # org/model and bare model leaf
        if "/" in bare:
            leaf = bare.rsplit("/", 1)[-1]
            add(leaf, "openrouter")
            # common zai mapping
            if bare.startswith("zai-org/"):
                add("z-ai/" + leaf, "openrouter")
                add(leaf, "openrouter")

    # custom:* providers rarely have local price tables — try openrouter by model id/leaf
    if raw_provider and raw_provider.startswith("custom"):
        add(raw_model, "openrouter")
        if "/" in raw_model:
            add(raw_model.rsplit("/", 1)[-1], "openrouter")

    # copilot often stores bare model ids; try openrouter market estimate when not included
    if raw_provider in {"copilot", "github-copilot", "github"}:
        add(raw_model, "openrouter")
        if not raw_model.startswith("openai/") and raw_model.startswith(("gpt-", "o1", "o3", "o4")):
            add(f"openai/{raw_model}", "openrouter")

    # generic leaf fallback
    if "/" in raw_model:
        add(raw_model.rsplit("/", 1)[-1], "openrouter")

    return out


def estimate_micro_cost(
    *,
    model: str,
    provider: str | None = None,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cache_read_tokens: int = 0,
    cache_write_tokens: int = 0,
    reasoning_tokens: int = 0,
) -> dict[str, Any]:
    """Return {cost_micro_usd, cost_status, pricing_version, label}."""
    try:
        from agent.usage_pricing import CanonicalUsage, estimate_usage_cost
    except Exception:
        return {
            "cost_micro_usd": 0,
            "cost_status": "unknown",
            "pricing_version": None,
            "label": "n/a",
        }

    usage = CanonicalUsage(
        input_tokens=int(input_tokens or 0),
        output_tokens=int(output_tokens or 0),
        cache_read_tokens=int(cache_read_tokens or 0),
        cache_write_tokens=int(cache_write_tokens or 0),
        reasoning_tokens=int(reasoning_tokens or 0),
    )

    last_unknown: dict[str, Any] | None = None
    for cand_model, cand_provider in _candidate_routes(model, provider):
        try:
            result = estimate_usage_cost(cand_model, usage, provider=cand_provider)
        except Exception:
            continue
        status = getattr(result, "status", "unknown") or "unknown"
        amount = getattr(result, "amount_usd", None)
        version = getattr(result, "pricing_version", None)
        if status == "included":
            return {
                "cost_micro_usd": 0,
                "cost_status": "included",
                "pricing_version": version,
                "label": "included",
                "priced_as": {"model": cand_model, "provider": cand_provider},
            }
        if amount is None or status == "unknown":
            last_unknown = {
                "cost_micro_usd": 0,
                "cost_status": "unknown",
                "pricing_version": version,
                "label": "n/a",
            }
            continue
        micro = usd_to_micro(amount)
        return {
            "cost_micro_usd": micro,
            "cost_status": status,
            "pricing_version": version,
            "label": f"µ$ {micro}",
            "priced_as": {"model": cand_model, "provider": cand_provider},
        }

    return last_unknown or {
        "cost_micro_usd": 0,
        "cost_status": "unknown",
        "pricing_version": None,
        "label": "n/a",
    }
