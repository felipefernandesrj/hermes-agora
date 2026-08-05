from agora.ops.mailbox import is_valid_recipient, normalize_recipient, build_mailbox_action_brief
from agora.ops.sprint import looks_like_sprint_request, compile_sprint_from_message
from agora.ops.gates import evaluate_complete_gate, vault_handoffs_dir
from agora.ops.stream import read_stream_tail
from pathlib import Path


def test_mailbox_blocks_junk_handles():
    valid = {"agent-techlead", "agent-backend"}
    assert is_valid_recipient("agent-techlead", valid)
    assert not is_valid_recipient("tokens", valid)
    assert not is_valid_recipient("all", valid)
    assert normalize_recipient("agent-backend", valid) == "agent-backend"
    assert normalize_recipient("TODOS", valid) is None


def test_mailbox_brief():
    brief = build_mailbox_action_brief(
        "agent-techlead",
        [{"id": 1, "author_profile": "human", "message_id": 9, "body_snippet": "oi"}],
    )
    assert "MAILBOX" in brief
    assert "notif#1" in brief


def test_sprint_detect_and_dry_run():
    body = "Quero implementar o live stream do agente no dashboard Ágora com scroll."
    assert looks_like_sprint_request(body)
    out = compile_sprint_from_message(body=body, author="human", dry_run=True)
    assert out["ok"] and out["dry_run"]
    roles = [c["role"] for c in out["cards"]]
    assert "techlead" in roles
    assert "frontend" in roles


def test_gate_missing_without_evidence(tmp_path, monkeypatch):
    # point vault to empty temp via monkeypatch of helper
    import agora.ops.gates as gates
    monkeypatch.setattr(gates, "vault_handoffs_dir", lambda: tmp_path)
    monkeypatch.setattr(gates, "praca_posts_for_task", lambda task_id: [])
    g = evaluate_complete_gate("t_does_not_exist_zz")
    assert g["ok"] is False
    assert "handoff_vault" in g["missing"]


def test_stream_handles_missing_log():
    data = read_stream_tail("agent-nope-never", task_id="t_no_such_task_zzz")
    assert "text" in data
    assert data["exists"] in (False, True)
