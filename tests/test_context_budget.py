# tests/test_context_budget.py
import copy
import unittest
from engine.lhtm.context_budget import ContextBudget
from engine.lhtm.config import DEFAULT_CONFIG


def make_task(tid="T01"):
    return {
        "id": tid, "title": "Build API", "objective": "Add endpoint",
        "status": "active", "depends_on": [], "risk_level": "low",
        "allowed_paths": ["src/"], "allowed_commands": ["pytest"],
        "definition_of_done": ["test passes"], "artifacts": [], "evidence": [],
        "attempts": 1, "max_attempts": 3,
    }


def make_state():
    return {"schema_version": "1.0", "run_id": "r1", "goal": {"text": "Build a todo app", "hash": "h"*64},
            "phase": "EXECUTING", "mode": "SUPERVISED", "active_task_id": "T01",
            "policy": {}, "tasks": [make_task()], "current_step": 0}


class TestContextBudget(unittest.TestCase):
    def setUp(self):
        self.b = ContextBudget()
        self.state = make_state()
        self.task = self.state["tasks"][0]

    def test_includes_sections(self):
        ctx = self.b.build(self.state, self.task, DEFAULT_CONFIG)
        self.assertIn("Build a todo app", ctx)   # goal
        self.assertIn("Build API", ctx)          # task card
        self.assertIn("SUPERVISED", ctx)         # policy
        self.assertIn("untrusted", ctx.lower())  # headroom

    def test_includes_errors(self):
        ctx = self.b.build(self.state, self.task, DEFAULT_CONFIG, errors=["ImportError: x"])
        self.assertIn("ImportError: x", ctx)

    def test_budget_cap_honored(self):
        cfg = copy.deepcopy(DEFAULT_CONFIG)
        cfg["limits"]["max_context_tokens"] = 50
        ctx = self.b.build(self.state, self.task, cfg, errors=["e1"], excerpts=["x" * 1000])
        self.assertLessEqual(len(ctx), 50)

    def test_cascade_drops_excerpts_before_goal(self):
        cfg = copy.deepcopy(DEFAULT_CONFIG)
        cfg["limits"]["max_context_tokens"] = 120
        ctx = self.b.build(self.state, self.task, cfg, errors=["e1"], excerpts=["y" * 500])
        # goal must survive even at a tight budget
        self.assertIn("Build a todo app", ctx)
        self.assertNotIn("yyy", ctx)

    def test_truncates_excerpts(self):
        cfg = copy.deepcopy(DEFAULT_CONFIG)
        cfg["limits"]["max_context_tokens"] = 300
        cfg["limits"]["max_excerpt_chars"] = 30
        ctx = self.b.build(self.state, self.task, cfg, excerpts=["a" * 200])
        self.assertIn("truncated", ctx)


if __name__ == "__main__":
    unittest.main()
