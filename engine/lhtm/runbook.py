# engine/lhtm/runbook.py
"""Deterministic runbook runner (operator-authored, never LLM-driven)."""
import json
import re as _re
from pathlib import Path

from .safe_executor import SafeExecutor

STEP_ACTIONS = {"run_command", "write_file", "assert"}
REQUIRED_STEP_FIELDS = {"id", "action"}


class RunbookRunner:
    def __init__(self, config):
        self.config = config or {}

    def validate(self, runbook: dict) -> list[str]:
        errs = []
        if not isinstance(runbook, dict):
            return ["runbook must be a dict"]
        if runbook.get("runbook_version") != 1:
            errs.append("runbook_version must be 1")
        if not runbook.get("title"):
            errs.append("runbook missing title")
        steps = runbook.get("steps")
        if not isinstance(steps, list) or not steps:
            return errs + ["runbook missing steps (non-empty list)"]
        ids = set()
        for i, s in enumerate(steps):
            if not isinstance(s, dict):
                errs.append(f"step {i}: must be a dict")
                continue
            missing = sorted(REQUIRED_STEP_FIELDS - set(s))
            if missing:
                errs.append(f"step {i}: missing {missing}")
            if s.get("id") in ids:
                errs.append(f"step {i}: duplicate id '{s.get('id')}'")
            ids.add(s.get("id"))
            if s.get("action") not in STEP_ACTIONS:
                errs.append(f"step {i}: invalid action '{s.get('action')}'")
            if s.get("action") == "run_command" and not isinstance(s.get("args"), list):
                errs.append(f"step {i}: run_command requires args list")
            if s.get("action") == "write_file" and not s.get("path"):
                errs.append(f"step {i}: write_file requires path")
            if s.get("action") == "assert" and not s.get("path"):
                errs.append(f"step {i}: assert requires path")
        return errs

    def execute(self, runbook, base_dir, config=None, dry_run=False) -> dict:
        """Run steps in order; stop on first failure. Idempotent by step id."""
        errs = self.validate(runbook)
        if errs:
            return {"ok": False, "steps": [], "error": "; ".join(errs)}
        cfg = config or self.config
        exe = SafeExecutor(cfg)
        safe_title = _re.sub(r"[^A-Za-z0-9_.-]", "_", runbook["title"])
        state_path = Path(base_dir) / "runbooks" / f"{safe_title}.json"
        done = set()
        if state_path.exists():
            try:
                raw = json.loads(state_path.read_text(encoding="utf-8")).get("done", [])
            except (ValueError, OSError):
                raw = []
            if isinstance(raw, list):
                done = {d for d in raw if isinstance(d, str)}
        results = []
        for s in runbook["steps"]:
            if s["id"] in done:
                results.append({"id": s["id"], "action": s["action"], "ok": True,
                                "error": None, "skipped": True})
                continue
            if dry_run:
                results.append({"id": s["id"], "action": s["action"], "ok": True,
                                "error": None, "skipped": False, "dry_run": True})
                continue
            r = self._run_step(s, exe, base_dir)
            results.append(r)
            if not r["ok"]:
                return {"ok": False, "steps": results, "error": r["error"]}
            done.add(s["id"])
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(json.dumps({"done": sorted(done)}), encoding="utf-8")
        return {"ok": True, "steps": results, "error": None}

    def _run_step(self, s, exe, base_dir) -> dict:
        action = s["action"]
        sid = s["id"]
        if action == "run_command":
            r = exe.execute({"action": "run_command", "tool": s.get("tool", ""),
                             "args": list(s.get("args", []))},
                            {"allowed": True, "requires_approval": False}, {})
            return {"id": sid, "action": action, "ok": r["ok"], "error": r["error"],
                    "result": r.get("result")}
        path = self._resolve(s["path"], base_dir)
        if action == "write_file":
            r = exe.execute({"action": "write_file", "path": path, "content": s.get("content", "")},
                            {"allowed": True, "requires_approval": False}, {})
            return {"id": sid, "action": action, "ok": r["ok"], "error": r["error"],
                    "result": r.get("result")}
        if action == "assert":
            p = Path(path)
            if not p.exists():
                return {"id": sid, "action": action, "ok": False,
                        "error": f"assert file missing: {s['path']}"}
            contains = s.get("contains")
            if contains is not None:
                text = p.read_text(encoding="utf-8", errors="replace")
                if contains not in text:
                    return {"id": sid, "action": action, "ok": False,
                            "error": f"assert '{contains}' not found in {s['path']}"}
            return {"id": sid, "action": action, "ok": True, "error": None}
        return {"id": sid, "action": action, "ok": False,
                "error": f"unsupported action '{action}'"}

    @staticmethod
    def _resolve(path, base_dir):
        p = Path(path)
        return str(p) if p.is_absolute() else str(Path(base_dir) / p)
