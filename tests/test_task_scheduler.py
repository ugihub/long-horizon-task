# tests/test_task_scheduler.py
import unittest
from engine.lhtm.task_scheduler import TaskScheduler


def make_task(tid, status="pending", deps=(), risk="low", attempts=0, max_attempts=3):
    return {
        "id": tid, "title": tid, "objective": "", "status": status,
        "depends_on": list(deps), "risk_level": risk,
        "allowed_paths": [], "allowed_commands": [],
        "definition_of_done": [], "artifacts": [], "evidence": [],
        "attempts": attempts, "max_attempts": max_attempts,
    }


def make_state(tasks, phase="READY", mode="SUPERVISED", active_task_id=None):
    return {
        "schema_version": "1.0", "run_id": "x", "goal": {"text": "g", "hash": "h"*64},
        "phase": phase, "mode": mode, "active_task_id": active_task_id,
        "policy": {}, "tasks": tasks, "current_step": 0,
    }


class TestTaskScheduler(unittest.TestCase):
    def setUp(self):
        self.s = TaskScheduler()

    def test_picks_first_ready_pending(self):
        state = make_state([make_task("T01"), make_task("T02")])
        pick = self.s.pick_next(state)
        self.assertEqual(pick["id"], "T01")

    def test_skips_non_pending(self):
        state = make_state([make_task("T01", status="claimed_done"), make_task("T02")])
        pick = self.s.pick_next(state)
        self.assertEqual(pick["id"], "T02")

    def test_skips_task_with_unverified_dependency(self):
        tasks = [make_task("T01", deps=["T00"]), make_task("T02")]
        state = make_state(tasks)
        # T00 is not verified_done anywhere in the state task list
        pick = self.s.pick_next(state)
        self.assertEqual(pick["id"], "T02")

    def test_skips_over_attempt_task(self):
        state = make_state([make_task("T01", attempts=3, max_attempts=3)])
        pick = self.s.pick_next(state)
        self.assertIsNone(pick)

    def test_high_risk_needs_approval_unless_full_auto(self):
        state = make_state([make_task("T01", risk="high")], mode="SUPERVISED")
        pick = self.s.pick_next(state)
        self.assertEqual(pick["id"], "T01")
        self.assertTrue(pick.get("requires_approval"))

        state_full = make_state([make_task("T02", risk="high")], mode="FULL_AUTO")
        pick2 = self.s.pick_next(state_full)
        self.assertEqual(pick2["id"], "T02")
        self.assertFalse(pick2.get("requires_approval"))

    def test_dependency_verified_done_qualifies(self):
        tasks = [make_task("T00", status="verified_done"), make_task("T01", deps=["T00"])]
        state = make_state(tasks)
        pick = self.s.pick_next(state)
        self.assertEqual(pick["id"], "T01")

    def test_no_tasks_returns_none(self):
        state = make_state([])
        self.assertIsNone(self.s.pick_next(state))

    def test_promote_to_ready(self):
        state = make_state([make_task("T01")])
        self.s.promote_to_ready(state, "T01")
        self.assertEqual(state["tasks"][0]["status"], "ready")


if __name__ == "__main__":
    unittest.main()
