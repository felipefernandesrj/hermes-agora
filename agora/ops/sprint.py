"""Compile a human praça desire into a kanban sprint skeleton."""

from __future__ import annotations

import json
import re
import subprocess
import time
from pathlib import Path
from typing import Any, Optional

from agora.config import load_agora_config, roster_profiles

try:
    from hermes_constants import get_default_hermes_root
except Exception:  # pragma: no cover
    def get_default_hermes_root() -> Path:  # type: ignore
        return Path.home() / ".hermes"


_SPRINT_MARKERS = (
    "//sprint",
    "/sprint",
    "quero implementar",
    "preciso que",
    "implementar",
    "vamos fazer",
    "build",
    "criar feature",
)


def looks_like_sprint_request(body: str) -> bool:
    text = (body or "").strip().lower()
    if not text:
        return False
    if text.startswith("//sprint") or text.startswith("/sprint"):
        return True
    # human author + action verbs
    hits = sum(1 for m in _SPRINT_MARKERS if m in text)
    return hits >= 1 and len(text) >= 24


def vault_briefings_dir() -> Path:
    # Prefer configured Obsidian path via rag_revival if present; else default vault.
    cfg_path = get_default_hermes_root() / "config.yaml"
    vault = Path.home() / "Documents" / "Obsidian Vault"
    try:
        import yaml  # type: ignore

        raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        rr = raw.get("rag_revival") or {}
        if isinstance(rr, dict) and rr.get("vault_dir"):
            vault = Path(str(rr["vault_dir"]))
    except Exception:
        pass
    d = vault / "04 Referências" / "agora" / "briefings"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _role_plan(body: str) -> list[tuple[str, str]]:
    """Return list of (role, title_suffix) for cards."""
    text = body.lower()
    roles: list[tuple[str, str]] = []
    # always techlead root coordination handled by caller; children:
    if any(k in text for k in ("ui", "frontend", "dashboard", "css", "botão", "botao", "stream")):
        roles.append(("frontend", "UI/dashboard"))
    if any(k in text for k in ("api", "backend", "endpoint", "sqlite", "plugin_api", "worker", "pid")):
        roles.append(("backend", "backend/API"))
    if any(k in text for k in ("qa", "test", "e2e", "aceite", "validar")):
        roles.append(("qa", "QA/validação"))
    # default pair if nothing matched
    if not roles:
        roles = [("backend", "implementação"), ("frontend", "UI"), ("qa", "QA")]
    # PO oversight card light
    roles.append(("po", "fiscalização de fluxo"))
    return roles


def compile_sprint_from_message(
    *,
    body: str,
    author: str = "human",
    source_message_id: Optional[int] = None,
    workspace: str = "/home/felipi/workspace/hermes-agora",
    board: str = "agora",
    dry_run: bool = False,
) -> dict[str, Any]:
    """Create kanban cards + briefing files from a praça message.

    Uses ``hermes kanban create`` CLI so it respects the active board tooling.
    """
    cfg = load_agora_config()
    roster = cfg.get("roster") or {}
    plan = _role_plan(body)
    created: list[dict[str, Any]] = []
    briefings: list[str] = []
    stamp = time.strftime("%Y%m%d-%H%M%S")
    summary = re.sub(r"\s+", " ", body.strip())[:140]

    root_title = f"Sprint: {summary}"
    # root card for techlead
    root = {
        "role": "techlead",
        "assignee": roster.get("techlead", "agent-techlead"),
        "title": root_title[:120],
        "body": (
            f"Sprint gerado da praça (author={author}"
            f"{f', msg={source_message_id}' if source_message_id else ''}).\n\n"
            f"Pedido original:\n{body.strip()}\n\n"
            "Orquestre filhos, exija posts na #praca e handoffs no vault."
        ),
    }
    cards_spec = [root]
    for role, suffix in plan:
        assignee = roster.get(role, f"agent-{role}")
        cards_spec.append(
            {
                "role": role,
                "assignee": assignee,
                "title": f"{suffix}: {summary}"[:120],
                "body": (
                    f"Card filho da sprint '{summary}'.\n"
                    f"Role={role}. Workspace canônico: {workspace}.\n"
                    f"Origem praça msg={source_message_id}.\n\n"
                    "Obrigatório: checkpoint na #praca + handoff vault ao concluir."
                ),
            }
        )

    if dry_run:
        return {"ok": True, "dry_run": True, "cards": cards_spec}

    for spec in cards_spec:
        cmd = [
            "hermes",
            "kanban",
            "create",
            spec["title"],
            "--assignee",
            str(spec["assignee"]),
            "--priority",
            "2",
            "--workspace",
            f"dir:{workspace}",
            "--body",
            spec["body"],
            "--json",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        payload: dict[str, Any]
        try:
            # CLI may print warnings before JSON; find last {...}
            out = proc.stdout.strip()
            brace = out.find("{")
            payload = json.loads(out[brace:]) if brace >= 0 else {"raw": out}
        except Exception:
            payload = {"raw": proc.stdout, "stderr": proc.stderr, "code": proc.returncode}
        task_id = payload.get("id") if isinstance(payload, dict) else None
        created.append({"spec": spec, "result": payload, "ok": proc.returncode == 0})
        if task_id:
            bdir = vault_briefings_dir()
            bpath = bdir / f"{task_id}.md"
            bpath.write_text(
                (
                    f"# Briefing {task_id}\n\n"
                    f"- role: {spec['role']}\n"
                    f"- assignee: {spec['assignee']}\n"
                    f"- source_message_id: {source_message_id}\n"
                    f"- created: {stamp}\n\n"
                    f"## Pedido\n\n{body.strip()}\n\n"
                    f"## Foco deste card\n\n{spec['title']}\n\n"
                    "## Não fazer\n\n- Não reinventar o plugin\n"
                    "- Não trabalhar fora do workspace canônico\n"
                ),
                encoding="utf-8",
            )
            briefings.append(str(bpath))

    return {
        "ok": all(c.get("ok") for c in created),
        "created": created,
        "briefings": briefings,
        "roster": roster_profiles(cfg),
        "board": board,
    }
