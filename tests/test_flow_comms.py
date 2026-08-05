from agora.ops.flow_comms import (
    format_delivery_announce,
    format_po_block_alert,
    format_po_qa_request,
    format_qa_result,
)


def test_po_block_alert_mentions_po_and_techlead():
    body = format_po_block_alert(
        task_id="t_x",
        title="Backend APIs",
        assignee="agent-backend",
        reason="HTTP 429 rate limit",
    )
    assert "@agent-po" in body
    assert "@agent-techlead" in body
    assert "t_x" in body
    assert "429" in body


def test_delivery_asks_po_to_request_qa_and_names_implementer():
    body = format_delivery_announce(
        task_id="t_y",
        title="Menu canal",
        assignee="agent-frontend",
        summary="menu 3 pontinhos ok",
    )
    assert "@agent-frontend" in body
    assert "@agent-po" in body
    assert "@agent-qa" in body
    assert "t_y" in body


def test_po_qa_request_points_qa_to_implementer():
    body = format_po_qa_request(
        task_id="t_y",
        title="Menu canal",
        implementer="agent-frontend",
        summary="done",
    )
    assert "@agent-qa" in body
    assert "@agent-frontend" in body
    assert "PASS|FAIL" in body


def test_qa_fail_mentions_implementer():
    body = format_qa_result(
        task_id="t_y",
        title="Menu canal",
        implementer="agent-frontend",
        verdict="fail",
        details="botão excluir não protege #praca",
    )
    assert "**FAIL**" in body
    assert "@agent-frontend" in body
    assert "@agent-po" in body
