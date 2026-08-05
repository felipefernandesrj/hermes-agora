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


def cost_by_squad(window: str = "24h") -> list[dict[str, Any]]:
    since = int(time.time()) - _window_seconds(window)
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT COALESCE(squad, '') AS squad,
                   COALESCE(SUM(api_call_count),0) AS api_call_count,
                   COALESCE(SUM(input_tokens+output_tokens+cache_read_tokens+cache_write_tokens+reasoning_tokens),0) AS total_tokens,
                   COALESCE(SUM(cost_micro_usd),0) AS cost_micro_usd
            FROM agora_usage_events
            WHERE observed_at >= ?
            GROUP BY 1
            ORDER BY cost_micro_usd DESC, total_tokens DESC
            """,
            (since,),
        ).fetchall()
    out = []
    for r in rows:
        micro = int(r["cost_micro_usd"] or 0)
        out.append(
            {
                "squad": r["squad"] or "unknown",
                "api_call_count": int(r["api_call_count"] or 0),
                "total_tokens": int(r["total_tokens"] or 0),
                "cost_micro_usd": micro,
                "cost_usd": micro_to_usd_str(micro),
            }
        )
    return out


def cost_by_task(task_id: str) -> dict[str, Any]:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT
              COALESCE(SUM(api_call_count),0) AS api_call_count,
              COALESCE(SUM(input_tokens+output_tokens+cache_read_tokens+cache_write_tokens+reasoning_tokens),0) AS total_tokens,
              COALESCE(SUM(cost_micro_usd),0) AS cost_micro_usd
            FROM agora_usage_events
            WHERE task_id = ?
            """,
            (task_id,),
        ).fetchone()
        models = conn.execute(
            """
            SELECT model,
                   COALESCE(SUM(api_call_count),0) AS api_call_count,
                   COALESCE(SUM(input_tokens+output_tokens+cache_read_tokens+cache_write_tokens+reasoning_tokens),0) AS total_tokens,
                   COALESCE(SUM(cost_micro_usd),0) AS cost_micro_usd
            FROM agora_usage_events
            WHERE task_id = ?
            GROUP BY model
            ORDER BY total_tokens DESC
            """,
            (task_id,),
        ).fetchall()
    micro = int(row["cost_micro_usd"] or 0)
    return {
        "task_id": task_id,
        "api_call_count": int(row["api_call_count"] or 0),
        "total_tokens": int(row["total_tokens"] or 0),
        "cost_micro_usd": micro,
        "cost_usd": micro_to_usd_str(micro),
        "models": [
            {
                "model": m["model"],
                "api_call_count": int(m["api_call_count"] or 0),
                "total_tokens": int(m["total_tokens"] or 0),
                "cost_micro_usd": int(m["cost_micro_usd"] or 0),
                "cost_usd": micro_to_usd_str(int(m["cost_micro_usd"] or 0)),
            }
            for m in models
        ],
    }


def cost_timeseries(window: str = "24h", bucket: str = "hour") -> list[dict[str, Any]]:
    since = int(time.time()) - _window_seconds(window)
    b = "hour" if bucket not in {"hour", "day"} else bucket
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT bucket_start,
                   SUM(api_call_count) AS api_call_count,
                   SUM(total_tokens) AS total_tokens,
                   SUM(cost_micro_usd) AS cost_micro_usd
            FROM agora_usage_rollup
            WHERE bucket = ? AND bucket_start >= ?
            GROUP BY bucket_start
            ORDER BY bucket_start ASC
            """,
            (b, since),
        ).fetchall()
        if rows:
            return [
                {
                    "bucket_start": int(r["bucket_start"]),
                    "api_call_count": int(r["api_call_count"] or 0),
                    "total_tokens": int(r["total_tokens"] or 0),
                    "cost_micro_usd": int(r["cost_micro_usd"] or 0),
                    "cost_usd": micro_to_usd_str(int(r["cost_micro_usd"] or 0)),
                }
                for r in rows
            ]
        # fallback directly from events if rollup empty
        rows = conn.execute(
            """
            SELECT (observed_at / 3600) * 3600 AS bucket_start,
                   SUM(api_call_count) AS api_call_count,
                   SUM(input_tokens+output_tokens+cache_read_tokens+cache_write_tokens+reasoning_tokens) AS total_tokens,
                   SUM(cost_micro_usd) AS cost_micro_usd
            FROM agora_usage_events
            WHERE observed_at >= ?
            GROUP BY 1
            ORDER BY 1 ASC
            """,
            (since,),
        ).fetchall()
    return [
        {
            "bucket_start": int(r["bucket_start"]),
            "api_call_count": int(r["api_call_count"] or 0),
            "total_tokens": int(r["total_tokens"] or 0),
            "cost_micro_usd": int(r["cost_micro_usd"] or 0),
            "cost_usd": micro_to_usd_str(int(r["cost_micro_usd"] or 0)),
        }
        for r in rows
    ]
