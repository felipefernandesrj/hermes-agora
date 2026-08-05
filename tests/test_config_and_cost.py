from agora.config import load_agora_config, roster_profiles
from agora.cost.pricing import usd_to_micro, micro_to_usd_str
from agora.db.repo import init_db, connect
from agora.api.health import build_health
from agora.api.cost import cost_summary
import os
from pathlib import Path


def test_usd_micro_roundtrip():
    assert usd_to_micro("0.038410") == 38410
    assert micro_to_usd_str(38410) == "0.038410"


def test_config_defaults(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    cfg = load_agora_config()
    assert cfg["active_squad"] == "bravo"
    assert "techlead" in cfg["roster"]
    assert roster_profiles(cfg)


def test_db_and_health(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    # force default root via env used by hermes_constants if present
    db = init_db(tmp_path / "agora.db")
    assert db.exists()
    with connect(db) as conn:
        n = conn.execute("select count(*) c from agora_channels").fetchone()["c"]
        assert n >= 4
        # usage table exists
        conn.execute("select count(*) from agora_usage_events").fetchone()
    # health against custom db via monkeypatch of resolve path
    import agora.db.repo as repo
    monkeypatch.setattr(repo, "resolve_db_path", lambda: db)
    h = build_health()
    assert h["status"] in {"healthy", "degraded"}
    assert h["capabilities"]["db"] is True
    s = cost_summary("24h")
    assert s["cost_micro_usd"] == 0


def test_collector_noop(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    import agora.db.repo as repo
    db = init_db(tmp_path / "agora.db")
    monkeypatch.setattr(repo, "resolve_db_path", lambda: db)
    from agora.cost.collector import collect_once
    # no profiles state dbs -> zero inserts, no crash
    out = collect_once(profiles=["nope"])
    assert out["inserted_events"] == 0
