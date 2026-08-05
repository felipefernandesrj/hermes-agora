#!/usr/bin/env bash
set -euo pipefail
# PO watcher: only prints when board unhealthy (script stdout empty => silent cron)
export PYTHONPATH="/home/felipi/workspace/hermes-agora:${PYTHONPATH:-}"
# Prefer hermes venv python
PY="/home/felipi/.hermes/hermes-agent/.venv/bin/python"
if [[ ! -x "$PY" ]]; then PY=python3; fi
cd /home/felipi/workspace/hermes-agora
# inspect first
report="$($PY - <<'PY'
import json, sys
sys.path.insert(0, "/home/felipi/workspace/hermes-agora")
sys.path.insert(0, "/home/felipi/.hermes/hermes-agent")
from agora.ops.po_watch import inspect_board
print(json.dumps(inspect_board("agora", stale_seconds=900)))
PY
)"
healthy=$(printf '%s' "$report" | $PY -c 'import sys,json;print(json.load(sys.stdin).get("healthy", True))')
if [[ "$healthy" == "True" ]]; then
  # silent
  exit 0
fi
# publish via API helper
$PY - <<'PY'
import sys
sys.path.insert(0, "/home/felipi/workspace/hermes-agora")
sys.path.insert(0, "/home/felipi/.hermes/hermes-agent")
from agora.ops.po_watch import inspect_board
from dashboard.plugin_api import CreateMessageBody, create_channel_message
rep = inspect_board("agora", stale_seconds=900)
body = (rep.get("report") or "") + "\n\n@agent-techlead PO flag: há gargalo no board."
msg = create_channel_message(
    "planejamento",
    CreateMessageBody(body=body, author_type="agent", author_profile="agent-po"),
)
print(body)
print("published", (msg or {}).get("message", {}).get("id"))
PY
