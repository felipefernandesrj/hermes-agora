"""Agent live stream — tail worker/profile logs for dashboard UX."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Optional

try:
    from hermes_constants import get_default_hermes_root
except Exception:  # pragma: no cover
    def get_default_hermes_root() -> Path:  # type: ignore
        return Path.home() / ".hermes"


def _board_logs_dir(board: str = "agora") -> Path:
    return get_default_hermes_root() / "kanban" / "boards" / board / "logs"


def resolve_agent_stream(
    profile: str,
    *,
    task_id: Optional[str] = None,
    board: str = "agora",
    worker: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Resolve the best live log source for a profile.

    Preference:
    1. explicit task_id log
    2. active kanban worker for profile
    3. newest log mentioning profile (best-effort)
    """
    logs_dir = _board_logs_dir(board)
    chosen_task = (task_id or "").strip() or None
    worker_pid = None
    run_id = None
    mode = "none"

    if worker:
        chosen_task = chosen_task or str(worker.get("task_id") or "").strip() or None
        worker_pid = worker.get("worker_pid")
        run_id = worker.get("run_id")
        if chosen_task:
            mode = "kanban-worker"

    path: Optional[Path] = None
    if chosen_task:
        cand = logs_dir / f"{chosen_task}.log"
        if cand.exists():
            path = cand
            mode = mode if mode != "none" else "kanban-task"

    if path is None and logs_dir.exists():
        # newest log overall as weak fallback (still better than silence)
        logs = sorted(logs_dir.glob("t_*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
        if logs:
            path = logs[0]
            chosen_task = path.stem
            mode = "latest-log-fallback"

    return {
        "profile": profile,
        "mode": mode,
        "task_id": chosen_task,
        "run_id": run_id,
        "worker_pid": worker_pid,
        "log_path": str(path) if path else None,
        "exists": bool(path and path.exists()),
        "board": board,
    }


def read_stream_tail(
    profile: str,
    *,
    task_id: Optional[str] = None,
    board: str = "agora",
    worker: Optional[dict[str, Any]] = None,
    offset: int = 0,
    max_bytes: int = 64_000,
) -> dict[str, Any]:
    """Read a chunk of the agent live stream.

    ``offset`` is a byte offset into the log file. Use 0 then follow with
    returned ``next_offset`` for polling/WS-like UI updates.
    """
    meta = resolve_agent_stream(profile, task_id=task_id, board=board, worker=worker)
    path_s = meta.get("log_path")
    if not path_s:
        return {
            **meta,
            "offset": 0,
            "next_offset": 0,
            "eof": True,
            "text": "",
            "truncated": False,
            "observed_at": int(time.time()),
        }

    path = Path(path_s)
    size = path.stat().st_size if path.exists() else 0
    start = max(0, int(offset or 0))
    if start > size:
        start = 0
    # if first read and file huge, start near end
    if start == 0 and size > max_bytes:
        start = max(0, size - max_bytes)
        truncated_head = True
    else:
        truncated_head = False

    text = ""
    next_off = start
    if path.exists():
        with path.open("rb") as fh:
            fh.seek(start)
            raw = fh.read(int(max_bytes))
            next_off = fh.tell()
        text = raw.decode("utf-8", errors="replace")
        if truncated_head:
            text = "…[truncated head]…\n" + text

    return {
        **meta,
        "offset": start,
        "next_offset": next_off,
        "size": size,
        "eof": next_off >= size,
        "text": text,
        "truncated": truncated_head,
        "observed_at": int(time.time()),
    }
