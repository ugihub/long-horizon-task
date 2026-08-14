# engine/lhtm/action_gate.py
"""Deterministic validation of every proposed action (SECURITY CORE)."""
import re
import fnmatch
from pathlib import Path

ACTION_TYPES = {"read_file", "list_files", "search_code", "write_file", "delete_file", "run_command", "ask_user"}

# Destructive command patterns (from policies/security.md). Matched on the
# joined tool+args string. Always rejected, regardless of allowlist.
DESTRUCTIVE_PATTERNS = [
    r"rm\s+-rf", r"rm\s+-r\s*/\b", r"sudo", r"su\b", r"chmod\s+777", r"chown",
    r"curl.*\|\s*(ba)?sh", r"wget.*-\s*O\s*-.*\|\s*sh",
    r"git\s+push.*--force", r"git\s+push\s+-f",
    r"\bDROP\s+DATABASE", r"\bDROP\s+TABLE", r"\bTRUNCATE\b",
    r":\(\s*\)\s*\{\s*:\|:\s*&\s*\}",
]


def _path_allowed(path: str, allowed_paths: list) -> bool:
    """True if path is equal to, under, or glob-matched by an allowed path."""
    p = Path(path).resolve()
    for a in allowed_paths:
        a = a.rstrip("/\\")
        base = Path(a).resolve()
        # exact file or a directory prefix
        if p == base or p.is_relative_to(base):
            return True
        # glob form (e.g. *.py)
        if fnmatch.fnmatch(path, a) or fnmatch.fnmatch(p.name, a):
            return True
    return False


def _is_sensitive(path: str, blocked_paths: list) -> bool:
    # Normalize separators so Windows backslash paths match dir blocklist patterns.
    low = path.replace("\\", "/").lower()
    for pat in blocked_paths:
        pat = pat.lower()
        if pat.endswith("/"):
            if low.startswith(pat) or pat[:-1] in low.split("/"):
                return True
        elif fnmatch.fnmatch(low, pat) or fnmatch.fnmatch(Path(low).name, pat):
            return True
        elif pat in low:
            return True
    return False


class ActionGate:
    def check(self, action: dict, task: dict, config: dict, mode: str, active_task_id: str) -> dict:
        """Return decision dict: allowed/reason/requires_approval/diff."""
        if action.get("action") not in ACTION_TYPES:
            return {"allowed": False, "reason": f"Unknown action type '{action.get('action')}'",
                    "requires_approval": False, "diff": None}
        if task.get("id") != active_task_id:
            return {"allowed": False, "reason": f"Task {task.get('id')} is not the active task",
                    "requires_approval": False, "diff": None}

        atype = action["action"]
        blocked = config.get("blocked_paths", [])

        if atype == "ask_user":
            return {"allowed": True, "reason": "ok", "requires_approval": False, "diff": None}

        # NOTE: sensitive-blocklist check runs BEFORE the allowed-path check.
        # Rule 4: blocked paths are rejected ALWAYS, regardless of allowed_paths.
        # (test_read_sensitive_blocked reads ".env", which is outside allowed_paths;
        # it must still be rejected for being sensitive, not for path.)
        if atype in ("read_file", "list_files", "delete_file"):
            path = action.get("path", "")
            if _is_sensitive(path, blocked):
                return {"allowed": False, "reason": f"Path '{path}' is sensitive/blocked",
                        "requires_approval": False, "diff": None}
            if not _path_allowed(path, task.get("allowed_paths", [])):
                return {"allowed": False, "reason": f"Path '{path}' is not allowed",
                        "requires_approval": False, "diff": None}
            if atype == "delete_file":
                return {"allowed": True, "reason": "ok", "requires_approval": mode != "FULL_AUTO", "diff": None}
            return {"allowed": True, "reason": "ok", "requires_approval": False, "diff": None}

        if atype == "search_code":
            path = action.get("path", "")
            if _is_sensitive(path, blocked):
                return {"allowed": False, "reason": f"Path '{path}' is sensitive/blocked",
                        "requires_approval": False, "diff": None}
            if not _path_allowed(path, task.get("allowed_paths", [])):
                return {"allowed": False, "reason": f"Path '{path}' is not allowed",
                        "requires_approval": False, "diff": None}
            return {"allowed": True, "reason": "ok", "requires_approval": False, "diff": None}

        if atype == "write_file":
            path = action.get("path", "")
            if _is_sensitive(path, blocked):
                return {"allowed": False, "reason": f"Path '{path}' is sensitive/blocked",
                        "requires_approval": False, "diff": None}
            if not _path_allowed(path, task.get("allowed_paths", [])):
                return {"allowed": False, "reason": f"Path '{path}' is not allowed",
                        "requires_approval": False, "diff": None}
            overwrite = Path(path).resolve().exists()
            need_approval = mode != "FULL_AUTO"
            if overwrite and config.get("approval", {}).get("require_for_file_overwrite", True):
                need_approval = True
            diff = None
            if overwrite:
                try:
                    diff = Path(path).read_text(encoding="utf-8", errors="replace")
                except OSError:
                    diff = None
            return {"allowed": True, "reason": "ok", "requires_approval": need_approval, "diff": diff}

        if atype == "run_command":
            tool = action.get("tool", "")
            args = action.get("args")
            if not isinstance(args, list) or not all(isinstance(x, str) for x in args):
                return {"allowed": False, "reason": "Command args must be a list",
                        "requires_approval": False, "diff": None}
            cmd = " ".join([tool] + args)
            if any(re.search(pat, cmd.lower()) for pat in DESTRUCTIVE_PATTERNS):
                return {"allowed": False, "reason": f"Command '{cmd}' is destructive",
                        "requires_approval": False, "diff": None}
            allowed = config.get("allowed_commands", [])
            if not any(cmd == a or cmd.startswith(a + " ") for a in allowed):
                return {"allowed": False, "reason": f"Command '{cmd}' not in allowlist",
                        "requires_approval": False, "diff": None}
            return {"allowed": True, "reason": "ok", "requires_approval": mode != "FULL_AUTO", "diff": None}
