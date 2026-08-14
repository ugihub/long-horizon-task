# engine/lhtm/audit.py
"""Structured audit logging to events.jsonl."""
import json
from datetime import datetime, timezone


class AuditLogger:
    def __init__(self, events_path: str):
        self.events_path = events_path

    def log(self, event: dict) -> None:
        entry = dict(event)
        entry.setdefault("ts", datetime.now(timezone.utc).isoformat())
        with open(self.events_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def log_step(self, run_id: str, phase: str, active_task_id: str,
                 action: str, result: str, duration_ms: int) -> None:
        self.log({
            "event": "step",
            "run_id": run_id,
            "phase": phase,
            "active_task_id": active_task_id,
            "action": action,
            "result": result,
            "duration_ms": duration_ms,
        })
