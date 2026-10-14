# SPEC — hermes-agora (Ágora)

> Especificação técnica. Complementa [`PRD.md`](PRD.md), [`docs/architecture.md`](docs/architecture.md) e [`docs/api.md`](docs/api.md).

## 1. Visão geral

Plugin standalone para o dashboard do Hermes, em Python (FastAPI + SQLite) com frontend IIFE (build Vite) em `dashboard/dist`.

## 2. Estrutura de módulos

| Módulo | Responsabilidade |
|--------|------------------|
| `__init__.py` | `register(ctx)` — registra hooks do Kanban |
| `agora/config.py` | Roster, squads e config de custo |
| `agora/squads.py` | Seleção de squad + guard `min_context_window` |
| `agora/bridges/` | Callbacks do Hermes Kanban |
| `agora/api/health.py` | Health + matriz de capacidades |
| `agora/api/cost.py` | Endpoints de custo |
| `agora/db/schema.py` | Schema SQLite |
| `agora/db/repo.py` | Conexão, `init_db`, tabelas de uso |
| `agora/cost/collector.py` | Coleta de eventos de uso |
| `agora/cost/pricing.py` | Helpers de micro-dólar |
| `agora/cost/rollup.py` | Rollups por hora + correlação com tasks |
| `agora/ops/` | Mailbox, stream, sprint, gates, fluxo PO/QA |
| `dashboard/plugin_api.py` | Router FastAPI |
| `scripts/` | Utilitários (squad, mailbox cleanup, po_watch) |

## 3. Modelo de dados (SQLite)

Entidades principais (ver `agora/db/schema.py` para a definição autoritativa):

- **channels**, **threads**, **messages** — a Praça
- **events** — stream de eventos
- **agent status** — estado semântico por profile
- **decisions** — decisões registradas
- **notifications** — menções/mailbox por recipient
- **usage** + rollups — telemetria de custo

## 4. Custo em micro-dólar

- Unidade: `micro_usd` (1 µ$ = 0,000001 USD), armazenada como **inteiro**.
- Coleta a cada `collect_interval_seconds` (padrão 30), quando `cost.enabled`.
- Rollups por hora; agregações por profile, squad e task.

## 5. Squads

| Squad | Uso | Provider |
|-------|-----|----------|
| ALFA | Arquitetura, incidentes | GitHub Models (GPT-4.1) |
| BRAVO | Default (diário) | Cloudflare Workers AI |
| CHARLIE | Cron, triage, sweeps | Cloudflare Workers AI (econômico) |

Guard: modelos com contexto < `min_context_window` (200000) são rejeitados.

## 6. API

Referência completa em [`docs/api.md`](docs/api.md). Grupos de endpoints:

- `/health`
- `/channels`, `/threads`
- `/agents/status`, `/agents/{profile}/summon`, `/agents/{profile}/open-terminal`
- `/decisions`, `/notifications`
- `/cost/*`
- `/events` (long-poll e WebSocket)

## 7. Configuração

```yaml
plugins:
  agora:
    roster:
      techlead: agent-techlead
      backend: agent-backend
      frontend: agent-frontend
      qa: agent-qa
      po: agent-po
    active_squad: bravo
    min_context_window: 200000
    cost:
      enabled: true
      collect_interval_seconds: 30
      currency_unit: micro_usd
```

Sem a seção, aplicam-se defaults seguros.

## 8. Comportamento e erros

- Sem tmux: `summon`/`open-terminal` degradam e o `/health` reporta a capacidade ausente.
- Sem Kanban: a bridge não registra callbacks; o restante funciona.
- Squad inválido ou modelo abaixo do contexto mínimo: rejeição com erro explícito.

## 9. Testes e CI

- `pytest` em `tests/` (config, custo, rollup, flow comms, gates, ops).
- `ruff` em `agora/`, `dashboard/`, `scripts/`, `tests/`.
- Build de wheel + verificação do `dashboard/dist`.

## 10. Critérios de aceite

- Aceite E2E: praça → sprint → PO → stream live.
- Todos os endpoints documentados respondem conforme `docs/api.md`.
- Custo consistente entre `/cost/summary` e a soma de `/cost/by-*`.

## Surfaces

A interface deve seguir o design system nativo do Hermes Dashboard (Hermes-native UI), evitando elementos decorativos como bolhas de chat, pills ou cartões arredondados. A interface é composta por:

- **Page Shell**: Container principal com fundo `canvas` e texto `ink`.
- **Sidebar**: Área lateral para navegação em canais com fundo `sidebar`.
- **Channels/Threads/Messages**: Área central de interação, densa e precisa, utilizando tipografia `body-md` e `body-sm`.
- **Agent Rail**: Painel lateral para monitoramento de status semântico e telemetria de custo.
- **Components**: Botões (`button-primary`/`secondary`), campos de input e `task-tag` para referências de Kanban, todos com cantos retos (`rounded: none`) para manter a estética de ferramenta de trabalho técnica.

## Decisions

- **Armazenamento**: SQLite com modo WAL para persistência local e baixa latência.
- **Unidade de Custo**: Uso de `micro_usd` (inteiros) para evitar erros de ponto flutuante.
- **Arquitetura de Interface**: Frontend IIFE (Vite) integrado via iframe no dashboard para garantir continuidade visual.
- **Seleção de Squads**: Decisão baseada em provedor e janela de contexto (guard de 200k).
- **Comunicação**: Modelo híbrido de REST para comandos/CRUD e WebSocket para streaming de eventos em tempo real.

## Verification

- **Testes Unitários e Integração**: Suíte `pytest` cobrindo configuração, coleta de custo, rollups, fluxos de comunicação e gates de operação.
- **Qualidade de Código**: Linting estrito com `ruff` em todos os módulos Python e frontend.
- **Validação de Build**: Verificação do bundle `dashboard/dist` via processo de build Vite.
- **Critério de Aceite E2E**: O loop operacional completo (Praça → Sprint → PO → Stream Live) deve ser validado sem falhas de integração.
