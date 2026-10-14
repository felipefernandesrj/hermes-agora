# BACKBONE · Hermes Ágora

The rules the project does not break. It is what an assessor checks beyond "it compiles".

## Rules

- **Guard de Contexto**: Qualquer modelo com `context_window` < 200k é rejeitado automaticamente pelo sistema de squads.
- **Degradação Graciosa**: O plugin deve continuar operando se `tmux` ou `Kanban` estiverem ausentes, reportando a capacidade reduzida via `/health`.
- **Protocolo de Erro**: Bloqueios ou crashes de tarefas devem disparar alertas imediatos via menções (`@agent-po`) nos canais de planejamento e praça.
- **Fluxo de QA**: Toda tarefa completada exige um pedido de teste automático ao `@agent-qa`, seguindo o template PASS/FAIL.
- **Integridade de Dados**: Coleta de telemetria deve ocorrer em intervalos fixos (padrão 30s) para garantir a precisão dos rollups por hora.

## Vocabulary

- **Ágora**: A praça pública local para deliberação de agentes.
- **Squads (ALFA/BRAVO/CHARLIE)**: Grupos de agentes com diferentes perfis de modelos e provedores.
- **µ$ (micro-dólar)**: Unidade atômica de medida de custo (1 µ$ = 0,000001 USD).
- **Summon**: Comando para invocar um agente para uma tarefa ou discussão.
- **Rollup**: Agregação de dados de uso por períodos (ex: por hora).
- **Gate**: Ponto de decisão ou validação (ex: fluxo PO/QA).
- **Roster**: Lista de mapeamento entre papéis (techlead, po, qa) e seus respectivos perfis de agentes.
