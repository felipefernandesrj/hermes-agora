"""Flow communications: PO escalation, delivery announce, QA request."""

from __future__ import annotations

from typing import Any, Optional


def format_po_block_alert(
    *,
    task_id: str,
    title: str,
    assignee: Optional[str],
    reason: Optional[str],
) -> str:
    who = assignee or "sem-assignee"
    mention_impl = f"@{who}" if who.startswith("agent-") else who
    lines = [
        f"🚨 @agent-po @agent-techlead BLOQUEIO no board",
        "",
        f"**{title}** (`{task_id}`)",
        f"Assignee: {mention_impl}",
    ]
    if reason:
        lines.extend(["", f"Motivo: {reason}"])
    else:
        lines.extend(["", "Motivo: (não informado)"])
    lines.extend(
        [
            "",
            "Ação PO: iluminar o gargalo e pedir desbloqueio.",
            "Ação techlead: diagnosticar (log/provider/429/protocol), desbloquear, failover se preciso, re-dispatch.",
            "Humano não precisa intervir salvo decisão de produto/custo.",
        ]
    )
    return "\n".join(lines)


def format_delivery_announce(
    *,
    task_id: str,
    title: str,
    assignee: Optional[str],
    summary: Optional[str],
    result: Optional[str] = None,
    verified_cards: Optional[list[str]] = None,
    artifacts: Optional[list[str]] = None,
) -> str:
    impl = assignee or "não atribuído"
    impl_m = f"@{impl}" if str(impl).startswith("agent-") else str(impl)
    report = (summary or result or "").strip()
    lines = [
        f"✅ Entrega concluída — {impl_m}",
        "",
        f"**{title}** (`{task_id}`)",
        f"Implementador: {impl_m}",
        "Status: done",
    ]
    if report:
        lines.extend(["", "Relatório:", report])
    else:
        lines.extend(["", "⚠️ Sem relatório de entrega."])
    if verified_cards:
        lines.extend(["", "Cards criados:"])
        lines.extend(f"- {c}" for c in verified_cards)
    if artifacts:
        lines.extend(["", "Artifacts:"])
        lines.extend(f"- {a}" for a in artifacts)
    lines.extend(
        [
            "",
            f"@agent-po solicite teste do @agent-qa nesta entrega e peça retorno mencionando {impl_m} para ajustes.",
            "@agent-techlead ciência da entrega.",
        ]
    )
    return "\n".join(lines)


def format_po_qa_request(
    *,
    task_id: str,
    title: str,
    implementer: Optional[str],
    summary: Optional[str] = None,
) -> str:
    impl = implementer or "agent-backend"
    impl_m = f"@{impl}" if str(impl).startswith("agent-") else f"@{impl}"
    lines = [
        f"🧪 @agent-qa TESTE solicitado pelo PO",
        "",
        f"Card: `{task_id}` — **{title}**",
        f"Implementador: {impl_m}",
    ]
    if summary:
        lines.extend(["", "Contexto da entrega:", str(summary).strip()[:800]])
    lines.extend(
        [
            "",
            "O que fazer:",
            "1. Validar a implementação no dashboard/API conforme o card",
            "2. Registrar evidências (passos, prints/logs, ids)",
            "3. Postar na #praca o veredito PASS/FAIL",
            f"4. Se FAIL: mencionar {impl_m} com o ajuste necessário e @agent-po / @agent-techlead",
            "5. Se PASS: mencionar @agent-po e @agent-techlead para fechar",
            "",
            "Template de resposta QA:",
            f"`[QA] {task_id} PASS|FAIL — ...; implementador {impl_m}; evidências: ...`",
        ]
    )
    return "\n".join(lines)


def format_qa_result(
    *,
    task_id: str,
    title: str,
    implementer: Optional[str],
    verdict: str,
    details: str,
) -> str:
    impl = implementer or "agent-backend"
    impl_m = f"@{impl}" if str(impl).startswith("agent-") else f"@{impl}"
    v = (verdict or "").strip().upper() or "FAIL"
    if v not in {"PASS", "FAIL"}:
        v = "FAIL"
    lines = [
        f"[QA] `{task_id}` **{v}** — {title}",
        f"Implementador: {impl_m}",
        "",
        details.strip() or "(sem detalhes)",
        "",
    ]
    if v == "FAIL":
        lines.append(
            f"{impl_m} ajuste necessário. @agent-po @agent-techlead ciência do FAIL."
        )
    else:
        lines.append("@agent-po @agent-techlead QA PASS — pode fechar/seguir.")
    return "\n".join(lines)


def extract_artifacts(metadata: Any) -> list[str]:
    if not isinstance(metadata, dict):
        return []
    raw = metadata.get("artifacts")
    if not isinstance(raw, (list, tuple)):
        return []
    return [str(a).strip() for a in raw if isinstance(a, str) and str(a).strip()]
