"""Collect usage deltas from Hermes profile state.db files into agora_usage_events."""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Any, Optional

from agora.config import load_agora_config, roster_profiles
from agora.cost.pricing import estimate_micro_cost, usd_to_micro
from agora.db.repo import connect

try:
    from hermes_constants import get_hermes_home
except Exception:  # pragma: no cover
    def get_hermes_home() -> Path:  # type: ignore
        return Path.home() / ".hermes"


def _profile_state_db(profile: str) -> Path:
    home = get_hermes_home()
    # default profile uses root state.db; named profiles live under profiles/
    if profile in {"", "default", "main"}:
        return home / "state.db"
    return home / "profiles" / profile / "state.db"


def _open_ro(path: Path) -> Optional[sqlite3.Connection]:
    if not path.exists():
        return None
    uri = f"file:{path}?mode=ro"
    try:
        conn = sqlite3.connect(uri, uri=True, timeout=2.0)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception:
        return None


def _get_watermark(conn: sqlite3.Connection, profile: str) -> float:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS agora_collector_state (
          key TEXT PRIMARY KEY,
          value TEXT NOT NULL
        )
        """
    )
    row = conn.execute(
        "SELECT value FROM agora_collector_state WHERE key = ?",
        (f"usage_wm::{profile}",),
    ).fetchone()
    if not row:
        return 0.0
    try:
        return float(row["value"] if isinstance(row, sqlite3.Row) else row[0])
    except Exception:
        return 0.0


def _set_watermark(conn: sqlite3.Connection, profile: str, value: float) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS agora_collector_state (
          key TEXT PRIMARY KEY,
          value TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "INSERT INTO agora_collector_state(key, value) VALUES(?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (f"usage_wm::{profile}", str(value)),
    )


def _has_table(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    ).fetchone()
    return bool(row)


def collect_once(*, profiles: Optional[list[str]] = None) -> dict[str, Any]:
    cfg = load_agora_config()
    squad = str(cfg.get("active_squad") or "")
    targets = profiles or roster_profiles(cfg)
    inserted = 0
    scanned = 0
    errors: list[str] = []
    now = int(time.time())

    with connect() as out:
        for profile in targets:
            scanned += 1
            sdb = _profile_state_db(profile)
            src = _open_ro(sdb)
            if src is None:
                continue
            try:
                if not _has_table(src, "session_model_usage"):
                    continue
                wm = _get_watermark(out, profile)
                rows = src.execute(
                    """
                    SELECT session_id, model, billing_provider, billing_base_url, billing_mode,
                           api_call_count, input_tokens, output_tokens, cache_read_tokens,
                           cache_write_tokens, reasoning_tokens,
                           estimated_cost_usd, actual_cost_usd, cost_status, cost_source,
                           first_seen, last_seen
                    FROM session_model_usage
                    WHERE COALESCE(last_seen, first_seen, 0) > ?
                    ORDER BY COALESCE(last_seen, first_seen, 0) ASC
                    """,
                    (wm,),
                ).fetchall()
                max_seen = wm
                for r in rows:
                    last = float(r["last_seen"] or r["first_seen"] or 0)
                    if last > max_seen:
                        max_seen = last
                    status = (r["cost_status"] or "unknown").strip() or "unknown"
                    amount = r["actual_cost_usd"]
                    if amount in (None, "", 0, 0.0):
                        amount = r["estimated_cost_usd"]
                    micro = 0
                    if status == "included":
                        micro = 0
                    elif amount not in (None, "", 0, 0.0) and status not in {"unknown", ""}:
                        micro = usd_to_micro(amount)
                    else:
                        # Recompute when Hermes stored 0/unknown (common for custom CF routes).
                        est = estimate_micro_cost(
                            model=r["model"],
                            provider=r["billing_provider"] or None,
                            input_tokens=r["input_tokens"] or 0,
                            output_tokens=r["output_tokens"] or 0,
                            cache_read_tokens=r["cache_read_tokens"] or 0,
                            cache_write_tokens=r["cache_write_tokens"] or 0,
                            reasoning_tokens=r["reasoning_tokens"] or 0,
                        )
                        micro = int(est["cost_micro_usd"])
                        if est["cost_status"] != "unknown":
                            status = est["cost_status"]
                    out.execute(
                        """
                        INSERT INTO agora_usage_events (
                          profile, squad, session_id, task_id, run_id, model, provider,
                          billing_mode, api_call_count, input_tokens, output_tokens,
                          cache_read_tokens, cache_write_tokens, reasoning_tokens,
                          cost_micro_usd, cost_status, pricing_version, observed_at
                        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                        """,
                        (
                            profile,
                            squad,
                            r["session_id"],
                            None,
                            None,
                            r["model"],
                            r["billing_provider"] or "",
                            r["billing_mode"] or "",
                            int(r["api_call_count"] or 0),
                            int(r["input_tokens"] or 0),
                            int(r["output_tokens"] or 0),
                            int(r["cache_read_tokens"] or 0),
                            int(r["cache_write_tokens"] or 0),
                            int(r["reasoning_tokens"] or 0),
                            int(micro),
                            status,
                            r["cost_source"],
                            now,
                        ),
                    )
                    inserted += 1
                if max_seen > wm:
                    _set_watermark(out, profile, max_seen)
                out.commit()
            except Exception as exc:
                errors.append(f"{profile}: {type(exc).__name__}: {exc}")
            finally:
                src.close()
    return {
        "scanned_profiles": scanned,
        "inserted_events": inserted,
        "errors": errors,
        "observed_at": now,
    }
