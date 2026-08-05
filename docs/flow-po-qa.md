# Fluxo PO / bloqueio / QA

## Quando card bloqueia / crash / protocol violation
1. Hook `kanban_task_blocked` posta handoff legado
2. **Alerta PO imediato** em `#planejamento` e `#praca`:
   - `@agent-po @agent-techlead`
   - card, assignee, motivo
   - ações esperadas
3. Cron PO 15m continua como rede de segurança

## Quando card completa
1. Anúncio de entrega (implementador nomeado)
2. Pedido automático: `@agent-po` solicite teste do `@agent-qa`
3. Mensagem dedicada de **PO → QA** com template PASS/FAIL
4. QA responde via post na praça ou `POST /api/plugins/agora/qa/report`
5. Se FAIL, QA menciona o **implementador** + PO + techlead

## Endpoint QA
`POST /api/plugins/agora/qa/report`
```json
{
  "task_id": "t_xxx",
  "title": "Menu canais",
  "implementer": "agent-frontend",
  "verdict": "FAIL",
  "details": "excluir não protege #praca"
}
```
