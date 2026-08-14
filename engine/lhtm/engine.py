# engine/lhtm/engine.py
import json
from datetime import datetime, timezone
from .state_store import StateStore
from .schema_validator import SchemaValidator
from .goal_hash import GoalHash
from .markdown_view import MarkdownView
from .evidence_verifier import EvidenceVerifier
from .recovery import RecoveryOrchestrator
from .project_facts import ProjectFacts
from .constants import EXECUTION_MODES, DEFAULT_POLICY

# Phase after a plan is submitted, per Implementation_plan.md §4.4 (12 phases).
PHASE_AFTER_LOAD = "PLAN_REVIEW"

class LhtmEngine:
    def __init__(self, base_dir: str):
        self.store = StateStore(base_dir)
        self.validator = SchemaValidator()
        self.view = MarkdownView()
        self.verifier = EvidenceVerifier()
        self.recovery = RecoveryOrchestrator()
        self.state = self.store.load_state()
        # ensure policy defaults
        if not self.state.get("policy"):
            self.state["policy"] = dict(DEFAULT_POLICY)

    def _save(self):
        # guardrail: canonical state must stay valid; reject corrupt writes before disk
        errs = self.validator.validate_state(self.state)
        if errs:
            raise ValueError("Refusing to save invalid state: " + "; ".join(errs))
        self.store.acquire_lock()
        try:
            self.store.save_state(self.state)
        finally:
            self.store.release_lock()

    def _log_event(self, event: str, task_id: str = None, data: dict = None):
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "task_id": task_id,
            "data": data or {},
        }
        with open(self.store.events_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def set_goal(self, text: str):
        self.state["goal"] = GoalHash.freeze(text)
        self._log_event("goal.frozen", data={"hash": self.state["goal"]["hash"]})
        self._save()

    def load_plan(self, plan: dict):
        errs = self.validator.validate_plan(plan)
        if errs:
            raise ValueError(f"Invalid plan: {'; '.join(errs)}")
        # ensure goal_hash matches
        if plan["goal_hash"] != self.state["goal"]["hash"]:
            raise ValueError("Plan goal_hash does not match current goal")
        self.state["tasks"] = plan["tasks"]
        self.state["phase"] = PHASE_AFTER_LOAD
        self._log_event("plan.submitted")
        self._save()

    def approve_plan(self):
        self.state["phase"] = "READY"
        self._log_event("plan.approved")
        self._save()

    def activate_task(self, task_id: str):
        task = self._find_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        if task["status"] != "ready":
            raise ValueError(f"Task {task_id} status is '{task['status']}', must be 'ready'")
        # lhtm_core rule #2: one active task at a time
        active = self.state.get("active_task_id")
        if active is not None and active != task_id:
            raise ValueError(f"Task {active} is already active; only one active task allowed")
        max_attempts = task.get("max_attempts", self.state.get("policy", {}).get("max_attempts", 3))
        if task.get("attempts", 0) >= max_attempts:
            raise ValueError(f"Task {task_id} exhausted max_attempts={max_attempts}; propose 'failed'")
        self.state["active_task_id"] = task_id
        task["status"] = "active"
        task["attempts"] = task.get("attempts", 0) + 1
        self.state["phase"] = "EXECUTING"
        self._log_event("task.activated", task_id)
        self._save()

    def set_mode(self, mode: str):
        mode = mode.upper()
        if mode not in EXECUTION_MODES:
            raise ValueError(f"invalid mode '{mode}'. Must be one of {EXECUTION_MODES}")
        self.state["mode"] = mode
        self._log_event("mode.changed", data={"mode": mode})
        self._save()

    def recover(self, task_id: str, action: dict) -> dict:
        """Validate + apply a recovery action. Saves on success, returns {'ok': bool}."""
        policy = self.state.get("policy", {})
        errs = self.recovery.validate_action(self.state, task_id, action, policy)
        if errs:
            return {"ok": False, "error": "; ".join(errs)}
        task = self._find_task(task_id)  # validate_action guarantees the task exists
        result = self.recovery.apply(self.state, task, action, policy)
        if not result.get("ok"):
            return result
        # a recovered task is no longer active
        # note: this also clears the active task when the action is
        # switch_to_safe_mode (no task status change). Spec behavior; revisit
        # if a task must stay active while lowering mode.
        self.state["active_task_id"] = None
        self._log_event("recovery.action", task_id, data={"action": action.get("action")})
        self._save()
        return {"ok": True, "error": None}

    def refresh_facts(self, repo_root: str = ".", allowed_paths: list | None = None,
                      config: dict | None = None) -> str:
        """Scan allowed_paths into .lhtm/project_facts.md (generated view)."""
        if allowed_paths is None:
            allowed_paths = list({p for t in self.state.get("tasks", [])
                                  for p in t.get("allowed_paths", [])}) or ["."]
        facts = ProjectFacts(repo_root, config or {})
        text = facts.render(allowed_paths)
        (self.store.base_dir / "project_facts.md").write_text(text, encoding="utf-8")
        return text

    def process_update(self, update: dict) -> dict:
        task_id = update.get("task_id")
        status = update.get("status")
        if not task_id or not status:
            return {"accepted": False, "errors": ["task_id and status required"]}

        # validate update schema
        errs = self.validator.validate_update(update)
        if errs:
            return {"accepted": False, "errors": errs}

        task = self._find_task(task_id)
        if not task:
            return {"accepted": False, "errors": [f"Task {task_id} not found"]}

        # check active task
        if task_id != self.state.get("active_task_id"):
            return {"accepted": False, "errors": [f"Task {task_id} is not active. Active: {self.state.get('active_task_id')}"]}

        # check transition is legal
        trans_errs = self.validator.validate_transition(task["status"], status)
        if trans_errs:
            return {"accepted": False, "errors": trans_errs}

        # apply update
        task["status"] = status
        if "evidence" in update:
            task["evidence"] = update["evidence"]
        if "artifacts" in update:
            task["artifacts"] = update["artifacts"]
        # attempts counted once per activation (see activate_task); no increment here

        # if failed, clear active task
        verdict = None
        feedback = None
        if status == "failed":
            self.state["active_task_id"] = None
            self._log_event("task.failed", task_id)
        elif status == "claimed_done":
            self._log_event("task.claimed_done", task_id)
            v = self.verifier.verify(self.state, task, {})
            verdict = v["verdict"]
            feedback = v["feedback"]
            if verdict == "pass":
                # engine-owned transition: verified_done is never settable by the LLM
                task["status"] = "verified_done"
                task.pop("feedback", None)  # clear stale failure feedback on retry-pass
                self.state["active_task_id"] = None
                self._log_event("task.verified", task_id)
            else:
                task["status"] = "failed"
                task["feedback"] = feedback
                self.state["active_task_id"] = None
                self._log_event("task.verify_failed", task_id)
        elif status == "blocked":
            self.state["active_task_id"] = None
            self._log_event("task.blocked", task_id)

        self._save()
        return {"accepted": True, "errors": [], "verdict": verdict, "feedback": feedback}

    def render_tracker(self) -> str:
        return self.view.render_tracker(self.state)

    def get_events(self, limit: int = 50) -> list[dict]:
        events = []
        if self.store.events_path.exists():
            with open(self.store.events_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        events.append(json.loads(line))
        return events[-limit:]

    def _find_task(self, task_id: str) -> dict | None:
        for t in self.state.get("tasks", []):
            if t["id"] == task_id:
                return t
        return None
