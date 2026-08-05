# Ágora ops scripts (Fase 1.5)

```bash
# mailbox hygiene
python scripts/agora_mailbox_cleanup.py

# PO watch (silent if healthy)
python scripts/agora_po_watch.py --board agora
python scripts/agora_po_watch.py --board agora --publish

# squad
python scripts/agora_squad.py list
```

Suggested cron (profile agent-po):
```
every 15m: python /home/felipi/workspace/hermes-agora/scripts/agora_po_watch.py --publish
```
