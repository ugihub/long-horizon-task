# tests/test_context_builder.py
import unittest
from engine.lhtm.context_builder import ContextBuilder
from engine.lhtm.config import DEFAULT_CONFIG


def make_task(tid="T01"):
    return {
        "id": tid, "title": "Build API", "objective": "Add endpoint",
        "status": "active", "depends_on": [], "risk_level": "low",
        "allowed_paths": ["src/"], "allowed_commands": ["pytest"],
        "definition_of_done": ["test passes"], "artifacts": [], "evidence": [],
        "attempts": 1, "max_attempts": 3,
    }


class TestContextBuilder(unittest.TestCase):
    def setUp(self):
        self.b = ContextBuilder()
        self.state = {
            "schema_version": "1.0", "run_id": "r1", "goal": {"text": "Build a todo app", "hash": "h"*64},
            "phase": "EXECUTING", "mode": "SUPERVISED", "active_task_id": "T01",
            "policy": {}, "tasks": [make_task()], "current_step": 0,
        }

    def test_includes_goal(self):
        ctx = self.b.build(self.state, self.state["tasks"][0], DEFAULT_CONFIG)
        self.assertIn("Build a todo app", ctx)

    def test_includes_task_card_fields(self):
        ctx = self.b.build(self.state, self.state["tasks"][0], DEFAULT_CONFIG)
        self.assertIn("Build API", ctx)
        self.assertIn("Add endpoint", ctx)
        self.assertIn("src/", ctx)

    def test_includes_untrusted_wrapper(self):
        ctx = self.b.build(self.state, self.state["tasks"][0], DEFAULT_CONFIG)
        self.assertIn("untrusted", ctx.lower())

    def test_includes_last_error(self):
        ctx = self.b.build(self.state, self.state["tasks"][0], DEFAULT_CONFIG, errors=["ImportError: x"])
        self.assertIn("ImportError: x", ctx)

    def test_mode_and_attempts(self):
        ctx = self.b.build(self.state, self.state["tasks"][0], DEFAULT_CONFIG)
        self.assertIn("SUPERVISED", ctx)
        self.assertIn("1/3", ctx)

    def test_redacts_secrets_in_output(self):
        ctx = self.b.build(self.state, self.state["tasks"][0], DEFAULT_CONFIG,
                           errors=["password: hunter2"])
        self.assertNotIn("hunter2", ctx)
        self.assertIn("[REDACTED]", ctx)


if __name__ == "__main__":
    unittest.main()
