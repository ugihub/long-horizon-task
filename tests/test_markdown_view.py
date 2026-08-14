# tests/test_markdown_view.py
import unittest
from engine.lhtm.markdown_view import MarkdownView
from engine.lhtm.goal_hash import GoalHash

class TestMarkdownView(unittest.TestCase):
    def setUp(self):
        self.view = MarkdownView()
        self.state = {
            "schema_version": "1.0",
            "run_id": "test-123",
            "goal": GoalHash.freeze("Build a todo app"),
            "phase": "EXECUTING",
            "mode": "SUPERVISED",
            "active_task_id": "T02",
            "policy": {"max_attempts": 3},
            "tasks": [
                {"id": "T01", "title": "Setup", "objective": "Init", "status": "verified_done",
                 "depends_on": [], "risk_level": "low", "allowed_paths": [], "allowed_commands": [],
                 "definition_of_done": ["exists"], "artifacts": [], "evidence": [{"type": "file", "path": "x"}],
                 "attempts": 1, "max_attempts": 3},
                {"id": "T02", "title": "Build", "objective": "Core", "status": "active",
                 "depends_on": ["T01"], "risk_level": "medium", "allowed_paths": [], "allowed_commands": [],
                 "definition_of_done": ["works"], "artifacts": [], "evidence": [],
                 "attempts": 0, "max_attempts": 3},
            ],
            "current_step": 2,
        }

    def test_render_includes_goal(self):
        md = self.view.render_tracker(self.state)
        self.assertIn("Build a todo app", md)

    def test_render_includes_phase(self):
        md = self.view.render_tracker(self.state)
        self.assertIn("EXECUTING", md)

    def test_render_includes_task_table(self):
        md = self.view.render_tracker(self.state)
        self.assertIn("T01", md)
        self.assertIn("T02", md)
        self.assertIn("Setup", md)
        self.assertIn("Build", md)

    def test_render_shows_active_indicator(self):
        md = self.view.render_tracker(self.state)
        self.assertIn("▶", md)  # active marker

    def test_render_evidence_checklist(self):
        md = self.view.render_tracker(self.state)
        self.assertIn("evidence", md.lower())

    def test_empty_state(self):
        state = {
            "schema_version": "1.0", "run_id": "x", "goal": GoalHash.freeze("do"),
            "phase": "DRAFT", "mode": "DRY_RUN", "active_task_id": None,
            "policy": {}, "tasks": [], "current_step": 0,
        }
        md = self.view.render_tracker(state)
        self.assertIn("DRAFT", md)

if __name__ == "__main__":
    unittest.main()
