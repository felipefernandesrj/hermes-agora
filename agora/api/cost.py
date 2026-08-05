"""Cost rollup queries."""

from __future__ import annotations

import time
from typing import Any, Optional

from agora.cost.pricing import micro_to_usd_str
from agora.db.repo import connect


def _window_seconds(window: str) -> int:
    w = (window or "24h").strip().lower()
    if w.endswith("d"):
        return int(float(w[:-1]) * 86400)
    if w.endswith("h"):
        return int(float(w[:-1]) * 3600)
    if w.endswith("m"):
        return int(float(w[:-1]) * 60)
    return 86400


def cost_summary(window: str = "24h") -> dict[str, Any]:
    since = int(time.time()) - _window_seconds(window)
    with connect() as conn:
        row = conn.execute(
            """
            SELECT
              COALESCE(SUM(api_call_count),0) AS api_call_count,
              COALESCE(SUM(input_tokens+output_tokens+cache_read_tokens+cache_write_tokens+reasoning_tokens),0) AS total_tokens,
              COALESCE(SUM(cost_micro_usd),0) AS cost_micro_usd
            FROM agora_usage_events
            WHERE observed_at >= ?
            """,
            (since,),
        ).fetchone()
    micro = int(row["cost_micro_usd"] or 0)
    return {
        "window": window,
        "api_call_count": int(row["api_call_count"] or 0),
        "total_tokens": int(row["total_tokens"] or 0),
        "cost_micro_usd": micro,
        "cost_usd": micro_to_usd_str(micro),
    }


def cost_by_profile(window: str = "24h") -> list[dict[str, Any]]:
    since = int(time.time()) - _window_seconds(window)
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT profile,
                   COALESCE(SUM(api_call_count),0) AS api_call_count,
                   COALESCE(SUM(input_tokens+output_tokens+cache_read_tokens+cache_write_tokens+reasoning_tokens),0) AS total_tokens,
                   COALESCE(SUM(cost_micro_usd),0) AS cost_micro_usd
            FROM agora_usage_events
            WHERE observed_at >= ?
            GROUP BY profile
            ORDER BY cost_micro_usd DESC, total_tokens DESC
            """,
            (since,),
        ).fetchall()
    out = []
    for r in rows:
        micro = int(r["cost_micro_usd"] or 0)
        out.append(
            {
                "profile": r["profile"],
                "api_call_count": int(r["api_call_count"] or 0),
                "total_tokens": int(r["total_tokens"] or 0),
                "cost_micro_usd": micro,
                "cost_usd": micro_to_usd_str(micro),
            }
        )
    return out
