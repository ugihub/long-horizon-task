# engine/lhtm/state_store.py
"""State persistence: atomic JSON save, O_EXCL lock w/ stale recovery, snapshots."""
import json
import os
import shutil
import time
import uuid
from pathlib import Path
from datetime import datetime, timezone

from .goal_hash import GoalHash
from .constants import SCHEMA_VERSION, DEFAULT_POLICY

LOCK_TIMEOUT = 5  # seconds
STALE_LOCK_SECONDS = 30


class StateStore:
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.state_path = self.base_dir / "state.json"
        self.lock_path = self.base_dir / "state.json.lock"
        self.snapshots_dir = self.base_dir / "snapshots"
        self.events_path = self.base_dir / "events.jsonl"
        self.plans_dir = self.base_dir / "plans"
        self.artifacts_dir = self.base_dir / "artifacts"
        self.logs_dir = self.base_dir / "logs"
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        self.plans_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self._lock_fd = None

    def _default_state(self) -> dict:
        return {
            "schema_version": SCHEMA_VERSION,
            "run_id": uuid.uuid4().hex[:12],
            "goal": GoalHash.freeze("(no goal set)"),
            "phase": "DRAFT",
            "mode": "DRY_RUN",
            "active_task_id": None,
            "policy": dict(DEFAULT_POLICY),
            "tasks": [],
            "current_step": 0,
        }

    def acquire_lock(self, blocking: bool = True) -> bool:
        # stale-lock recovery: a lock file untouched for a while is dead
        self._clear_stale_lock()
        try:
            self._lock_fd = open(self.lock_path, "x")
            return True
        except FileExistsError:
            if not blocking:
                return False
            deadline = time.time() + LOCK_TIMEOUT
            while time.time() < deadline:
                self._clear_stale_lock()
                try:
                    self._lock_fd = open(self.lock_path, "x")
                    return True
                except FileExistsError:
                    time.sleep(0.1)
            return False

    def _clear_stale_lock(self):
        try:
            age = time.time() - os.path.getmtime(self.lock_path)
            if age > STALE_LOCK_SECONDS:
                self.lock_path.unlink(missing_ok=True)
        except FileNotFoundError:
            pass

    def release_lock(self):
        if self._lock_fd:
            self._lock_fd.close()
            self.lock_path.unlink(missing_ok=True)
            self._lock_fd = None

    def save_state(self, state: dict) -> None:
        if not self._lock_fd:
            raise RuntimeError("save_state requires holding the state lock")
        # atomic write: write to .tmp, then rename
        tmp = self.state_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
        tmp.replace(self.state_path)

    def load_state(self) -> dict:
        if not self.state_path.exists():
            return self._default_state()
        raw = self.state_path.read_text(encoding="utf-8")
        state = json.loads(raw)
        if not isinstance(state, dict):
            raise ValueError("state.json must be a JSON object")
        # validate goal hash on load
        GoalHash.check(state.get("goal", {}))
        return state

    def create_snapshot(self) -> str:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        snap_path = self.snapshots_dir / f"state-{ts}.json"
        if self.state_path.exists():
            shutil.copy2(self.state_path, snap_path)
        return str(snap_path)

    def restore_snapshot(self, path: str) -> None:
        src = Path(path)
        if not src.exists():
            raise FileNotFoundError(f"Snapshot not found: {path}")
        # atomic restore to avoid corrupting state on crash mid-copy
        tmp = self.state_path.with_suffix(".restore.tmp")
        shutil.copy2(src, tmp)
        tmp.replace(self.state_path)
