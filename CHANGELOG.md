# Changelog

## 1.0.0 — public release
- Backend modular: db/config/cost split into `agora/db`, `agora/api`, `agora/cost`
- Health endpoint with capability matrix (db/kanban/tmux/roster)
- Cost telemetry in micro-dólar (µ$): collector, pricing, rollups, task correlation
- Cost API: summary, by-profile, by-squad, by-task, timeseries
- Squad system: ALFA/BRAVO/CHARLIE with min_context_window guard
- Squad inspector/switcher script (`scripts/agora_squad.py`)
- CI: pytest + ruff lint + frontend dist check
- Docs: API reference (`docs/api.md`), architecture (`docs/architecture.md`)
- Anonymized all personal/internal references for public release

## 0.2.0 — packaging standalone
- Extraído do protótipo interno (`agora-prototype-v0`)
- Removidos paths absolutos de máquina local
- Instalável em `~/.hermes/plugins/agora`
- Skeleton de `agora/config.py` (roster/squads/cost)
- Hooks Kanban via `register(ctx)`

## 0.1.0 — protótipo interno
- Channels, messages, threads, agent status, decisions, notifications
- Summon / open-terminal / tmux wake
- Kanban callbacks
