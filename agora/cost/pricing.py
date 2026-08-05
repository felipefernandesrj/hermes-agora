"""Micro-dollar cost helpers. Prefer Hermes usage_pricing when available."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Optional

MICRO = Decimal("1000000")


def usd_to_micro(amount_usd: Any) -> int:
    if amount_usd is None:
        return 0
    try:
        d = Decimal(str(amount_usd))
    except Exception:
        return 0
    return int((d * MICRO).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def micro_to_usd_str(micro: int) -> str:
    d = (Decimal(int(micro or 0)) / MICRO).quantize(Decimal("0.000001"))
    return f"{d:.6f}"


def estimate_micro_cost(
    *,
    model: str,
    provider: Optional[str] = None,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cache_read_tokens: int = 0,
    cache_write_tokens: int = 0,
    reasoning_tokens: int = 0,
) -> dict[str, Any]:
    """Return {cost_micro_usd, cost_status, pricing_version, label}."""
    try:
        from agent.usage_pricing import CanonicalUsage, estimate_usage_cost

        usage = CanonicalUsage(
            input_tokens=int(input_tokens or 0),
            output_tokens=int(output_tokens or 0),
            cache_read_tokens=int(cache_read_tokens or 0),
            cache_write_tokens=int(cache_write_tokens or 0),
            reasoning_tokens=int(reasoning_tokens or 0),
        )
        result = estimate_usage_cost(model, usage, provider=provider)
        status = getattr(result, "status", "unknown") or "unknown"
        amount = getattr(result, "amount_usd", None)
        if status == "included":
            return {
                "cost_micro_usd": 0,
                "cost_status": "included",
                "pricing_version": getattr(result, "pricing_version", None),
                "label": "included",
            }
        if amount is None:
            return {
                "cost_micro_usd": 0,
                "cost_status": "unknown",
                "pricing_version": getattr(result, "pricing_version", None),
                "label": "n/a",
            }
        micro = usd_to_micro(amount)
        return {
            "cost_micro_usd": micro,
            "cost_status": status,
            "pricing_version": getattr(result, "pricing_version", None),
            "label": f"µ$ {micro}",
        }
    except Exception:
        return {
            "cost_micro_usd": 0,
            "cost_status": "unknown",
            "pricing_version": None,
            "label": "n/a",
        }
