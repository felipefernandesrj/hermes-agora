#!/usr/bin/env python3
"""Run PO board health check (optionally publish to #planejamento)."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path.home() / ".hermes" / "hermes-agent"))

from agora.ops.po_watch import inspect_board

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--board", default="agora")
    ap.add_argument("--stale-seconds", type=int, default=900)
    ap.add_argument("--publish", action="store_true")
    args = ap.parse_args()
    rep = inspect_board(args.board, stale_seconds=args.stale_seconds)
    print(json.dumps(rep, indent=2, ensure_ascii=False))
    if args.publish and rep.get("ok") and not rep.get("healthy"):
        from dashboard.plugin_api import create_channel_message, CreateMessageBody
        body = rep["report"] + "\n\n@agent-techlead PO flag: há gargalo no board."
        print(create_channel_message("planejamento", CreateMessageBody(body=body, author_type="agent", author_profile="agent-po")))

if __name__ == "__main__":
    main()
