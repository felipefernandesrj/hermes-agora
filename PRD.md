

## Problem

A coordenação de múltiplos agentes autônomos operando em diferentes modelos e provedores carece de uma camada de governança e visibilidade centralizada. Atualmente, há dificuldade em monitorar o contexto de trabalho (context window), rastrear o consumo de recursos de computação em granularidade fina (micro-dólar) e gerenciar fluxos de decisão e qualidade (PO/QA) de forma integrada ao dashboard de operação. Sem uma 'praça' de deliberação e um sistema de squads, a comunicação entre agentes e a rastreabilidade de custos por tarefa e perfil tornam-se fragmentadas.

## Goal

Implementar o Hermes Ágora, um plugin de dashboard para fornecer uma camada de governança, comunicação e telemetria para o ecossistema de agentes. O objetivo é estabelecer: 
1. **Ágora (Praça):** Um espaço de deliberação via canais e threads para agentes e humanos.
2. **Gestão de Squads:** Controle de modelos via squads (ALFA, BRAVO, CHARLIE) com guard de contexto mínimo (200k).
3. **Telemetria de Uso:** Coleta e rollup de consumo de computação em micro-dólares (µ$) por hora, perfil e task.
4. **Fluxos de Operação:** Automação de gates de QA (PASS/FAIL) e alertas de bloqueio via hooks do Kanban.
5. **Visibilidade de Status:** Monitoramento em tempo real da saúde do sistema e estado semântico dos agentes.

## Out of scope

- Desenvolvimento de novos modelos de LLM ou provedores de inferência.
- Gestão de infraestrutura de hardware (o plugin assume o provisionamento de compute).
- Interfaces de usuário fora do ecossistema de dashboard do Hermes.
- Implementação de fluxos de trabalho que não passem pelo contexto do Kanban ou da Ágora.
- Execução de tarefas que não dependam da infraestrutura de agentes já existente.
