# tests/test_engine.py
import unittest, tempfile, shutil, os
from engine.lhtm.engine import LhtmEngine
from engine.lhtm.goal_hash import GoalHash

class TestEngine(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.engine = LhtmEngine(self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_initialized_state(self):
        state = self.engine.state
        self.assertEqual(state["phase"], "DRAFT")
        self.assertEqual(state["mode"], "DRY_RUN")
        self.assertEqual(state["active_task_id"], None)

    def test_set_goal(self):
        self.engine.set_goal("Build a todo app")
        self.assertEqual(self.engine.state["goal"]["text"], "Build a todo app")
        self.assertEqual(len(self.engine.state["goal"]["hash"]), 64)

    def test_load_plan(self):
        self.engine.set_goal("Build app")
        plan = {
            "schema_version": "1.0",
            "run_id": self.engine.state["run_id"],
            "goal_hash": self.engine.state["goal"]["hash"],
            "title": "Plan", "objective": "Do",
            "tasks": [
                {"id": "T01", "title": "A", "objective": "", "status": "pending",
                 "depends_on": [], "risk_level": "low", "allowed_paths": [],
                 "allowed_commands": [], "definition_of_done": [], "artifacts": [],
                 "evidence": [], "attempts": 0, "max_attempts": 3},
            ],
            "open_questions": [], "metadata": {}, "approved": False,
        }
        self.engine.load_plan(plan)
        self.assertEqual(len(self.engine.state["tasks"]), 1)
        self.assertEqual(self.engine.state["phase"], "PLAN_REVIEW")

    def test_process_update(self):
        self.engine.set_goal("Build app")
        plan = {
            "schema_version": "1.0",
            "run_id": self.engine.state["run_id"],
            "goal_hash": self.engine.state["goal"]["hash"],
            "title": "Plan", "objective": "Do",
            "tasks": [
                {"id": "T01", "title": "A", "objective": "", "status": "pending",
                 "depends_on": [], "risk_level": "low", "allowed_paths": ["."],
                 "allowed_commands": [], "definition_of_done": [], "artifacts": [],
                 "evidence": [], "attempts": 0, "max_attempts": 3},
            ],
            "open_questions": [], "metadata": {}, "approved": False,
        }
        self.engine.load_plan(plan)
        self.engine.approve_plan()
        self.engine.state["tasks"][0]["status"] = "ready"  # scheduler promotes pending -> ready
        self.engine._save()
        self.engine.activate_task("T01")
        result = self.engine.process_update({"task_id": "T01", "status": "claimed_done",
                                             "evidence": [{"type": "observation", "note": "done"}]})
        self.assertTrue(result["accepted"])
        self.assertEqual(result["verdict"], "pass")
        self.assertEqual(self.engine.state["tasks"][0]["status"], "verified_done")
        self.assertIsNone(self.engine.state["active_task_id"])

    def test_activate_rejects_second_active_task(self):
        self.engine.set_goal("Build app")
        plan = {
            "schema_version": "1.0",
            "run_id": self.engine.state["run_id"],
            "goal_hash": self.engine.state["goal"]["hash"],
            "title": "Plan", "objective": "Do",
            "tasks": [
                {"id": "T01", "title": "A", "objective": "", "status": "pending",
                 "depends_on": [], "risk_level": "low", "allowed_paths": [],
                 "allowed_commands": [], "definition_of_done": [], "artifacts": [],
                 "evidence": [], "attempts": 0, "max_attempts": 3},
                {"id": "T02", "title": "B", "objective": "", "status": "pending",
                 "depends_on": [], "risk_level": "low", "allowed_paths": [],
                 "allowed_commands": [], "definition_of_done": [], "artifacts": [],
                 "evidence": [], "attempts": 0, "max_attempts": 3},
            ],
            "open_questions": [], "metadata": {}, "approved": False,
        }
        self.engine.load_plan(plan)
        self.engine.approve_plan()
        for t in self.engine.state["tasks"]:
            t["status"] = "ready"
        self.engine._save()
        self.engine.activate_task("T01")
        with self.assertRaises(ValueError):
            self.engine.activate_task("T02")

    def test_activate_rejects_exhausted_attempts(self):
        self.engine.set_goal("Build app")
        plan = {
            "schema_version": "1.0",
            "run_id": self.engine.state["run_id"],
            "goal_hash": self.engine.state["goal"]["hash"],
            "title": "Plan", "objective": "Do",
            "tasks": [
                {"id": "T01", "title": "A", "objective": "", "status": "pending",
                 "depends_on": [], "risk_level": "low", "allowed_paths": [],
                 "allowed_commands": [], "definition_of_done": [], "artifacts": [],
                 "evidence": [], "attempts": 3, "max_attempts": 3},
            ],
            "open_questions": [], "metadata": {}, "approved": False,
        }
        self.engine.load_plan(plan)
        self.engine.approve_plan()
        self.engine.state["tasks"][0]["status"] = "ready"
        self.engine._save()
        with self.assertRaises(ValueError):
            self.engine.activate_task("T01")

    def test_attempts_counted_once_per_activation(self):
        self.engine.set_goal("Build app")
        plan = {
            "schema_version": "1.0",
            "run_id": self.engine.state["run_id"],
            "goal_hash": self.engine.state["goal"]["hash"],
            "title": "Plan", "objective": "Do",
            "tasks": [
                {"id": "T01", "title": "A", "objective": "", "status": "pending",
                 "depends_on": [], "risk_level": "low", "allowed_paths": [],
                 "allowed_commands": [], "definition_of_done": [], "artifacts": [],
                 "evidence": [], "attempts": 0, "max_attempts": 3},
            ],
            "open_questions": [], "metadata": {}, "approved": False,
        }
        self.engine.load_plan(plan)
        self.engine.approve_plan()
        self.engine.state["tasks"][0]["status"] = "ready"
        self.engine._save()
        self.engine.activate_task("T01")
        self.engine.process_update({"task_id": "T01", "status": "claimed_done",
                                    "evidence": [{"type": "observation", "note": "done"}]})
        self.assertEqual(self.engine.state["tasks"][0]["attempts"], 1)

    def test_process_update_rejects_active_status(self):
        self.engine.set_goal("Build app")
        plan = {
            "schema_version": "1.0",
            "run_id": self.engine.state["run_id"],
            "goal_hash": self.engine.state["goal"]["hash"],
            "title": "Plan", "objective": "Do",
            "tasks": [
                {"id": "T01", "title": "A", "objective": "", "status": "pending",
                 "depends_on": [], "risk_level": "low", "allowed_paths": [],
                 "allowed_commands": [], "definition_of_done": [], "artifacts": [],
                 "evidence": [], "attempts": 0, "max_attempts": 3},
            ],
            "open_questions": [], "metadata": {}, "approved": False,
        }
        self.engine.load_plan(plan)
        self.engine.approve_plan()
        self.engine.state["tasks"][0]["status"] = "ready"
        self.engine._save()
        self.engine.activate_task("T01")
        # LLM cannot propose 'active' — engine owns activation
        result = self.engine.process_update({"task_id": "T01", "status": "active"})
        self.assertFalse(result["accepted"])
        self.assertTrue(any("active" in e for e in result["errors"]))

    def test_save_rejects_corrupt_state(self):
        self.engine.set_goal("Build app")
        self.engine.state["phase"] = "NOT_A_PHASE"
        with self.assertRaises(ValueError):
            self.engine._save()

    def test_process_update_rejects_engine_owned(self):
        self.engine.set_goal("Build app")
        result = self.engine.process_update({"task_id": "T01", "status": "verified_done"})
        self.assertFalse(result["accepted"])

    def test_process_update_rejects_illegal_transition(self):
        self.engine.set_goal("Build app")
        plan = {
            "schema_version": "1.0",
            "run_id": self.engine.state["run_id"],
            "goal_hash": self.engine.state["goal"]["hash"],
            "title": "Plan", "objective": "Do",
            "tasks": [
                {"id": "T01", "title": "A", "objective": "", "status": "pending",
                 "depends_on": [], "risk_level": "low", "allowed_paths": [],
                 "allowed_commands": [], "definition_of_done": [], "artifacts": [],
                 "evidence": [], "attempts": 0, "max_attempts": 3},
            ],
            "open_questions": [], "metadata": {}, "approved": False,
        }
        self.engine.load_plan(plan)
        self.engine.approve_plan()
        self.engine.state["tasks"][0]["status"] = "ready"  # scheduler promotes pending -> ready
        self.engine._save()
        self.engine.activate_task("T01")
        # illegal: pending -> active -> claimed_done is fine, but pending -> verified_done directly is not
        result = self.engine.process_update({"task_id": "T01", "status": "verified_done"})
        self.assertFalse(result["accepted"])

    def test_render_tracker(self):
        self.engine.set_goal("Build app")
        md = self.engine.render_tracker()
        self.assertIn("Build app", md)

    def test_events_logged(self):
        self.engine.set_goal("Build app")
        events = self.engine.get_events()
        self.assertGreaterEqual(len(events), 1)
        self.assertEqual(events[0]["event"], "goal.frozen")

    def test_claimed_done_bad_evidence_becomes_failed(self):
        self.engine.set_goal("Build app")
        plan = {
            "schema_version": "1.0",
            "run_id": self.engine.state["run_id"],
            "goal_hash": self.engine.state["goal"]["hash"],
            "title": "Plan", "objective": "Do",
            "tasks": [
                {"id": "T01", "title": "A", "objective": "", "status": "pending",
                 "depends_on": [], "risk_level": "low", "allowed_paths": ["."],
                 "allowed_commands": [], "definition_of_done": ["zork missing thing"],
                 "artifacts": [], "evidence": [], "attempts": 0, "max_attempts": 3},
            ],
            "open_questions": [], "metadata": {}, "approved": False,
        }
        self.engine.load_plan(plan)
        self.engine.approve_plan()
        self.engine.state["tasks"][0]["status"] = "ready"
        self.engine._save()
        self.engine.activate_task("T01")
        result = self.engine.process_update({"task_id": "T01", "status": "claimed_done",
                                             "evidence": [{"type": "observation", "note": "done"}]})
        self.assertTrue(result["accepted"])
        self.assertEqual(result["verdict"], "fail")
        self.assertEqual(self.engine.state["tasks"][0]["status"], "failed")
        self.assertIn("not covered", self.engine.state["tasks"][0]["feedback"])
        self.assertIsNone(self.engine.state["active_task_id"])

    def test_verified_done_event_logged(self):
        self.engine.set_goal("Build app")
        plan = {
            "schema_version": "1.0",
            "run_id": self.engine.state["run_id"],
            "goal_hash": self.engine.state["goal"]["hash"],
            "title": "Plan", "objective": "Do",
            "tasks": [
                {"id": "T01", "title": "A", "objective": "", "status": "pending",
                 "depends_on": [], "risk_level": "low", "allowed_paths": ["."],
                 "allowed_commands": [], "definition_of_done": [], "artifacts": [],
                 "evidence": [], "attempts": 0, "max_attempts": 3},
            ],
            "open_questions": [], "metadata": {}, "approved": False,
        }
        self.engine.load_plan(plan)
        self.engine.approve_plan()
        self.engine.state["tasks"][0]["status"] = "ready"
        self.engine._save()
        self.engine.activate_task("T01")
        self.engine.process_update({"task_id": "T01", "status": "claimed_done",
                                    "evidence": [{"type": "observation", "note": "done"}]})
        events = [e for e in self.engine.get_events() if e["event"] == "task.verified"]
        self.assertEqual(len(events), 1)

if __name__ == "__main__":
    unittest.main()
