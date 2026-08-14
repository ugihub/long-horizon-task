# engine/lhtm/recovery.py
"""Engine-orchestrated recovery actions. Deterministic; targets are legal transitions."""
from .constants import EXECUTION_MODES
from .schema_validator import SchemaValidator


class RecoveryOrchestrator:
    ACTIONS = {"retry_with_hint", "request_user_input", "mark_blocked",
               "decompose_task", "rollback_proposal", "switch_to_safe_mode"}

    # action name -> target task status (None = no task-status change)
    STATUS_TARGETS = {
        "retry_with_hint": "ready",
        "request_user_input": "blocked",
        "mark_blocked": "blocked",
        "rollback_proposal": "ready",
    }

    def __init__(self):
        self.validator = SchemaValidator()

    def validate_action(self, state, task_id, action, config=None) -> list[str]:
        """Return error list; [] if the action is valid for the task."""
        if not isinstance(action, dict):
            return ["recovery action must be a dict"]
        name = action.get("action")
        if name not in self.ACTIONS:
            return [f"unknown recovery action '{name}'"]
        task = next((t for t in state.get("tasks", []) if t.get("id") == task_id), None)
        if task is None:
            return [f"task {task_id} not found"]
        if name == "decompose_task":
            subs = action.get("proposed_subtasks")
            if not isinstance(subs, list) or not subs:
                return ["decompose_task requires non-empty proposed_subtasks"]
            # validate_plan checks fields/dup ids/depends_on/cycles/pending status.
            # NOTE: proposed_subtasks must NOT list the parent in depends_on; the
            # orchestrator adds the parent edge on apply.
            # the parent must be able to reach blocked legally (active/ready);
            # failed -> blocked is illegal, so a failed parent is rejected here
            parent_errs = self.validator.validate_transition(task.get("status"), "blocked")
            if parent_errs:
                return parent_errs
            plan = {"schema_version": "1.0", "goal_hash": "x" * 64, "tasks": subs,
                    "open_questions": [], "metadata": {}, "approved": False}
            return self.validator.validate_plan(plan)
        if name == "switch_to_safe_mode":
            target = (action.get("mode") or "SUPERVISED").upper()
            if target not in EXECUTION_MODES:
                return [f"invalid mode '{target}'. Must be one of {EXECUTION_MODES}"]
            if target == "FULL_AUTO":
                return ["switch_to_safe_mode cannot raise to FULL_AUTO"]
            return []
        target = self.STATUS_TARGETS[name]
        return self.validator.validate_transition(task.get("status"), target)

    def apply(self, state, task, action, config) -> dict:
        name = action.get("action")
        if name == "retry_with_hint":
            task["status"] = "ready"
            task["feedback"] = action.get("hint") or "retry with hint"
        elif name == "request_user_input":
            task["status"] = "blocked"
            task["feedback"] = action.get("question") or "waiting for user input"
        elif name == "mark_blocked":
            task["status"] = "blocked"
            task.pop("feedback", None)
        elif name == "rollback_proposal":
            task["status"] = "ready"
            task["feedback"] = "rolled back"
            task["evidence"] = []
            task["artifacts"] = []
        elif name == "decompose_task":
            task["status"] = "blocked"
            task["feedback"] = "decomposed into subtasks"
            subs = action.get("proposed_subtasks", [])
            for i, s in enumerate(subs):
                s["id"] = s.get("id") or f"{task['id']}-{i+1}"
                s["status"] = "pending"
                s.setdefault("attempts", 0)
                s.setdefault("max_attempts", task.get("max_attempts", 3))
                deps = list(s.get("depends_on", []))
                if task["id"] not in deps:
                    deps.insert(0, task["id"])
                s["depends_on"] = deps
            state["tasks"].extend(subs)
        elif name == "switch_to_safe_mode":
            target = (action.get("mode") or "SUPERVISED").upper()
            if target == "FULL_AUTO":
                return {"ok": False, "error": "switch_to_safe_mode cannot raise to FULL_AUTO"}
            state["mode"] = target
        return {"ok": True, "error": None}
