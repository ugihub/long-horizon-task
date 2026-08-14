# tests/test_recovery.py
import unittest
from engine.lhtm.recovery import RecoveryOrchestrator


def make_task(tid="T01", status="failed", risk="low"):
    return {
        "id": tid, "title": "t", "objective": "", "status": status,
        "depends_on": [], "risk_level": risk, "allowed_paths": ["src/"],
        "allowed_commands": [], "definition_of_done": [], "artifacts": [],
        "evidence": [], "attempts": 1, "max_attempts": 3,
    }


def make_state(tasks):
    return {"schema_version": "1.0", "run_id": "r", "goal": {"text": "g", "hash": "h"*64},
            "phase": "EXECUTING", "mode": "SUPERVISED", "active_task_id": None,
            "policy": {}, "tasks": tasks, "current_step": 0}


class TestRecovery(unittest.TestCase):
    def setUp(self):
        self.orc = RecoveryOrchestrator()

    def test_retry_failed_to_ready(self):
        state = make_state([make_task()])
        t = state["tasks"][0]
        errs = self.orc.validate_action(state, "T01", {"action": "retry_with_hint", "hint": "fix"}, {})
        self.assertEqual(errs, [])
        r = self.orc.apply(state, t, {"action": "retry_with_hint", "hint": "fix"}, {})
        self.assertTrue(r["ok"])
        self.assertEqual(t["status"], "ready")
        self.assertEqual(t["feedback"], "fix")
        self.assertEqual(t["attempts"], 1)  # NOT incremented by recovery

    def test_request_user_input_active_to_blocked(self):
        state = make_state([make_task(status="active")])
        t = state["tasks"][0]
        self.assertEqual(self.orc.validate_action(state, "T01", {"action": "request_user_input", "question": "go?"}), [])
        self.orc.apply(state, t, {"action": "request_user_input", "question": "go?"}, {})
        self.assertEqual(t["status"], "blocked")
        self.assertEqual(t["feedback"], "go?")

    def test_mark_blocked(self):
        state = make_state([make_task(status="active")])
        t = state["tasks"][0]
        self.orc.apply(state, t, {"action": "mark_blocked"}, {})
        self.assertEqual(t["status"], "blocked")

    def test_rollback_clears_evidence(self):
        state = make_state([make_task(status="failed", )])
        t = state["tasks"][0]
        t["evidence"] = [{"type": "file_created", "path": "src/x.py"}]
        t["artifacts"] = ["src/x.py"]
        self.orc.apply(state, t, {"action": "rollback_proposal"}, {})
        self.assertEqual(t["status"], "ready")
        self.assertEqual(t["evidence"], [])
        self.assertEqual(t["artifacts"], [])
        self.assertEqual(t["feedback"], "rolled back")

    def test_illegal_transition_rejected(self):
        # active -> ready is ILLEGAL; retry_with_hint (target ready) must be rejected
        state = make_state([make_task(status="active")])
        errs = self.orc.validate_action(state, "T01", {"action": "retry_with_hint", "hint": "x"}, {})
        self.assertTrue(any("illegal" in e for e in errs))

    def test_unknown_action_rejected(self):
        state = make_state([make_task()])
        errs = self.orc.validate_action(state, "T01", {"action": "explode"}, {})
        self.assertTrue(any("unknown" in e for e in errs))

    def test_decompose_creates_subtasks(self):
        state = make_state([make_task(status="active")])
        t = state["tasks"][0]
        subs = [
            {"id": "T01-a", "title": "a", "objective": "", "status": "pending",
             "depends_on": [], "risk_level": "low", "allowed_paths": ["src/"],
             "allowed_commands": [], "definition_of_done": [], "artifacts": [],
             "evidence": [], "attempts": 0, "max_attempts": 3},
        ]
        errs = self.orc.validate_action(state, "T01", {"action": "decompose_task", "proposed_subtasks": subs}, {})
        self.assertEqual(errs, [])
        r = self.orc.apply(state, t, {"action": "decompose_task", "proposed_subtasks": subs}, {})
        self.assertTrue(r["ok"])
        self.assertEqual(t["status"], "blocked")
        self.assertEqual(len(state["tasks"]), 2)
        # subtask depends on parent, which is NOT in the sub-task's own list
        self.assertIn("T01", state["tasks"][1]["depends_on"])

    def test_switch_to_safe_mode_rejects_full_auto(self):
        state = make_state([make_task()])
        errs = self.orc.validate_action(state, "T01", {"action": "switch_to_safe_mode", "mode": "FULL_AUTO"}, {})
        self.assertTrue(any("FULL_AUTO" in e for e in errs))
        r = self.orc.apply(state, state["tasks"][0], {"action": "switch_to_safe_mode", "mode": "FULL_AUTO"}, {})
        self.assertFalse(r["ok"])

    def test_switch_to_safe_mode_lowers_mode(self):
        state = make_state([make_task()])
        self.orc.apply(state, state["tasks"][0], {"action": "switch_to_safe_mode", "mode": "DRY_RUN"}, {})
        self.assertEqual(state["mode"], "DRY_RUN")

    def test_decompose_on_failed_rejected(self):
        # failed -> blocked is illegal (failed only allows ready); decompose must reject
        state = make_state([make_task(status="failed")])
        subs = [{"id": "T01-a", "title": "a", "objective": "", "status": "pending",
                 "depends_on": [], "risk_level": "low", "allowed_paths": ["src/"],
                 "allowed_commands": [], "definition_of_done": [], "artifacts": [],
                 "evidence": [], "attempts": 0, "max_attempts": 3}]
        errs = self.orc.validate_action(state, "T01", {"action": "decompose_task", "proposed_subtasks": subs}, {})
        self.assertTrue(any("illegal" in e for e in errs))


if __name__ == "__main__":
    unittest.main()
