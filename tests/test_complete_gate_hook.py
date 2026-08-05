import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# load plugin module as package root __init__
import importlib.util
spec = importlib.util.spec_from_file_location("agora_plugin_root", ROOT / "__init__.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_complete_gate_blocks_missing_task_evidence():
    out = mod._pre_tool_call("kanban_complete", {"task_id": "t_definitely_missing_zzz"})
    assert isinstance(out, dict)
    assert out.get("action") == "block"
    assert "Missing" in out.get("message", "") or "missing" in out.get("message", "").lower()


def test_complete_gate_allows_known_smoke_when_evidence_present():
    # t_d8f75f07 has handoff + praca posts in this environment
    out = mod._pre_tool_call("kanban_complete", {"task_id": "t_d8f75f07"})
    assert out is None


def test_non_complete_tools_pass():
    assert mod._pre_tool_call("read_file", {"path": "x"}) is None
