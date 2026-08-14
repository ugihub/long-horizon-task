# engine/lhtm/safe_executor.py
"""Execute actions that passed the ActionGate. SUPERVISED default."""
import os
import re
import shutil
import subprocess
from pathlib import Path

from .redactor import Redactor

# Cap redactor input so pathological command output cannot stall the executor.
OVERSHOOT = 1_000_000


class SafeExecutor:
    def __init__(self, config: dict):
        self.config = config
        self._limit = config.get("limits", {}).get("max_log_chars_sent_to_model", 3000)
        self._redact = config.get("security", {}).get("redact_secrets", True)
        self._redactor = Redactor.from_config(config)

    def execute(self, action: dict, decision: dict, task: dict) -> dict:
        if not decision.get("allowed"):
            return {"ok": False, "action": action.get("action"), "result": None,
                    "error": decision.get("reason", "action not allowed")}
        if decision.get("requires_approval") and not decision.get("approval_granted"):
            return {"ok": False, "action": action.get("action"), "result": None,
                    "error": "requires user approval"}
        if decision.get("dry_run"):
            return {"ok": True, "action": action.get("action"), "result": "dry-run", "error": None}
        atype = action.get("action")
        try:
            if atype == "write_file":
                return self._write_file(action)
            if atype == "delete_file":
                return self._delete_file(action)
            if atype == "read_file":
                return self._read_file(action)
            if atype == "list_files":
                return self._list_files(action)
            if atype == "search_code":
                return self._search_code(action)
            if atype == "run_command":
                return self._run_command(action)
            return {"ok": False, "action": atype, "result": None,
                    "error": f"unknown action type '{atype}'"}
        except Exception as e:  # noqa: BLE001 - executor returns errors, not raises
            return {"ok": False, "action": atype, "result": None, "error": str(e)}

    def _write_file(self, action):
        path = Path(action["path"])
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            bak = path.with_suffix(path.suffix + ".bak")
            shutil.copy2(path, bak)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(action.get("content", ""), encoding="utf-8")
        tmp.replace(path)
        return {"ok": True, "action": "write_file", "result": str(path), "error": None}

    def _delete_file(self, action):
        path = Path(action["path"])
        trash = path.parent.parent / ".trash"
        trash.mkdir(parents=True, exist_ok=True)
        target = trash / path.name
        n = 1
        while target.exists():
            target = trash / f"{path.stem}.{n}{path.suffix}"
            n += 1
        path.rename(target)
        return {"ok": True, "action": "delete_file", "result": str(target), "error": None}

    def _read_file(self, action):
        path = Path(action["path"])
        return {"ok": True, "action": "read_file",
                "result": path.read_text(encoding="utf-8", errors="replace"), "error": None}

    def _list_files(self, action):
        path = Path(action.get("path", "."))
        names = sorted(str(p) for p in path.rglob("*") if p.is_file())
        return {"ok": True, "action": "list_files", "result": names[:100], "error": None}

    def _search_code(self, action):
        pattern = action.get("pattern", "")
        path = Path(action.get("path", "."))
        rx = re.compile(pattern)
        hits = []
        for p in path.rglob("*"):
            if not p.is_file():
                continue
            try:
                for i, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                    if rx.search(line):
                        hits.append(f"{p}:{i}: {line.strip()[:120]}")
            except OSError:
                continue
        return {"ok": True, "action": "search_code", "result": hits[:50], "error": None}

    def _run_command(self, action):
        cmd = [action.get("tool", "")] + list(action.get("args", []))
        try:
            timeout = self.config.get("limits", {}).get("max_cmd_timeout", 60)
            proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                                  errors="replace", timeout=timeout)
        except subprocess.TimeoutExpired:
            return {"ok": False, "action": "run_command", "result": None, "error": "command timed out"}
        out = (proc.stdout or "") + (proc.stderr or "")
        out = out.strip()
        if self._redact:
            # cap the redactor input so pathological output cannot stall the
            # process: redact a bounded prefix, then truncate to the model limit.
            # A secret split exactly at the overshoot edge is the residual risk,
            # accepted for log context. (ponytail: raise OVERSHOOT if command
            # output legitimately exceeds it and redaction latency matters.)
            out = self._redactor.redact(out[:OVERSHOOT]) if len(out) > OVERSHOOT else self._redactor.redact(out)
        if len(out) > self._limit:
            out = out[: self._limit] + f"\n... (truncated {len(out) - self._limit} chars)"
        if proc.returncode != 0:
            return {"ok": False, "action": "run_command", "result": out,
                    "error": f"command exited with code {proc.returncode}"}
        return {"ok": True, "action": "run_command", "result": out, "error": None}
