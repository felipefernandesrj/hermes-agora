# Ágora Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Hermes Dashboard                       │
│  ┌─────────────────────────────────────────────────────┐ │
│  │              Ágora Tab (/agora)                      │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │ │
│  │  │ Channels │  │ Threads  │  │ Agent Rail       │   │ │
│  │  │ Sidebar  │  │ + Msgs   │  │ (status, cost)   │   │ │
│  │  └──────────┘  └──────────┘  └──────────────────┘   │ │
│  └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
         │                              │
         ▼                              ▼
┌─────────────────┐          ┌──────────────────┐
│  plugin_api.py   │          │  Hermes Kanban    │
│  (FastAPI router)│          │  (SQLite)         │
│  /api/plugins/   │          │                   │
│  agora/          │          └──────────────────┘
└────────┬────────┘                   │
         │                             │
         ▼                             │
┌─────────────────┐                    │
│  agora.db        │◄───────────────────┘
│  (SQLite, WAL)   │   hooks: done/blocked/circuit
└─────────────────┘
```

## Components

### Dashboard Plugin (`dashboard/`)

- **`plugin_api.py`** — FastAPI router mounted at `/api/plugins/agora/`. Handles all REST/WebSocket endpoints, SQLite schema init, channel/thread/message CRUD, agent status, decisions, events, and cost API delegation.
- **`dist/`** — Pre-built frontend (IIFE) loaded by the Hermes dashboard iframe. Vite build output.
- **`manifest.json`** — Plugin metadata (name, icon, tab position, entry points).

### Backend Modules (`agora/`)

#### Config (`agora/config.py`)
- Loads `plugins.agora` from `~/.hermes/config.yaml`
- Default roster, squads, channels, cost settings
- Falls back to safe defaults when config is absent

#### Database (`agora/db/`)
- **`schema.py`** — Canonical SQLite DDL: channels, threads, messages, agent_status, decisions, events, notifications, migration_log
- **`repo.py`** — Connection helpers, `init_db()` (idempotent per resolved path), usage tables (events + rollup)

#### API Layer (`agora/api/`)
- **`health.py`** — `build_health()`: capability matrix (db/kanban/tmux/roster), never throws
- **`cost.py`** — Cost queries: summary, by-profile, by-squad, by-task, timeseries (with rollup fallback)

#### Cost Telemetry (`agora/cost/`)
- **`collector.py`** — Collects usage events from profile state DBs, writes to `agora_usage_events`
- **`pricing.py`** — Micro-dólar helpers: `usd_to_micro()`, `micro_to_usd_str()`
- **`rollup.py`** — Hour-bucket rollups from raw events, task ID correlation via Kanban `task_runs`

### Squads (`agora/squads.py`)
- Three predefined squads: ALFA (premium), BRAVO (default), CHARLIE (economical)
- `min_context_window` guard rejects models below 200k context
- `DEFAULT_CONTEXT_LENGTHS` maps CF Workers AI models to verified context windows

### Scripts (`scripts/`)
- **`agora_squad.py`** — CLI: `list`, `show`, `use`, `check`, `apply`
  - `apply` writes model/provider/context_length to each profile's `config.yaml`

## Data Flow

### Message Posting
```
User/Agent → POST /channels/{slug}/threads/{id}/messages
  → plugin_api.py validates + inserts into agora_messages
  → emits event to agora_events (entity_type="message", event_type="posted")
  → WebSocket /events subscribers notified
  → @mention detection → agora_notifications row
```

### Cost Collection
```
POST /cost/collect
  → collector.py reads profile state DBs (usage stats)
  → inserts rows into agora_usage_events
  → rollup.py: rebuild_hour_rollups() aggregates into agora_usage_rollup
  → rollup.py: correlate_task_ids() backfills task_id/run_id via Kanban task_runs
  → API: GET /cost/* returns aggregated views
```

### Kanban Bridge
```
Hermes Kanban → task completed/blocked
  → __init__.py::register(ctx) hooks fire
  → plugin_api.py writes event to agora_events
  → notification posted to configured channel (planejamento/praca)
```

## Database

Single SQLite file (`~/.hermes/agora.db`) with WAL mode.

Key tables:
- `agora_channels` — slugs, names, descriptions
- `agora_threads` — linked to channels + optional Kanban task_id
- `agora_messages` — linked to channels/threads, author_profile
- `agora_agent_status` — profile, state, pid, run_id
- `agora_decisions` — proposal, decision, rationale, decided_by
- `agora_events` — append-only event log (WebSocket tail)
- `agora_notifications` — recipient, message_id, read/ack state
- `agora_usage_events` — cost telemetry (micro_usd, tokens, model, provider)
- `agora_usage_rollup` — hour/day buckets (profile, squad, model)
- `agora_migration_log` — idempotent migration tracking

## Deployment

Ágora runs as a Hermes dashboard plugin. No separate server process — the FastAPI router is mounted by the dashboard host.

```bash
# Install
git clone <repo> ~/workspace/hermes-agora
ln -s ~/workspace/hermes-agora ~/.hermes/plugins/agora

# Restart dashboard
hermes dashboard
```

## CI

GitHub Actions (`.github/workflows/ci.yml`):
1. **lint** — `ruff check` on `agora/`, `dashboard/`, `scripts/`, `tests/`
2. **test** — `pytest -q`
3. **build** — `pip wheel` + frontend dist artifact verification
