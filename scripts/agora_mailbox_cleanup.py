#!/usr/bin/env python3
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path.home() / ".hermes" / "hermes-agent"))
from agora.db.repo import connect
from agora.ops.mailbox import cleanup_invalid_notifications
with connect() as conn:
    print(json.dumps(cleanup_invalid_notifications(conn), indent=2))
