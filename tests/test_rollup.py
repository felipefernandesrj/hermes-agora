import time
from agora.db.repo import init_db, connect
from agora.cost.rollup import rebuild_hour_rollups
from agora.api.cost import cost_timeseries, cost_by_squad


def test_rollup_and_timeseries(tmp_path, monkeypatch):
    import agora.db.repo as repo
    db = init_db(tmp_path / "agora.db")
    monkeypatch.setattr(repo, "resolve_db_path", lambda: db)
    now = int(time.time())
    with connect(db) as conn:
        conn.execute(
            """
            INSERT INTO agora_usage_events (
              profile, squad, session_id, model, provider, billing_mode,
              api_call_count, input_tokens, output_tokens, cache_read_tokens,
              cache_write_tokens, reasoning_tokens, cost_micro_usd, cost_status, observed_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                "agent-backend", "bravo", "s1", "qwen/qwen3-coder-plus", "openrouter", "",
                2, 1000, 200, 0, 0, 0, 1234, "estimated", now,
            ),
        )
        conn.commit()
    n = rebuild_hour_rollups(since=now - 10)
    assert n >= 1
    pts = cost_timeseries("24h")
    assert pts and pts[-1]["cost_micro_usd"] == 1234
    squads = cost_by_squad("24h")
    assert any(s["squad"] == "bravo" for s in squads)
