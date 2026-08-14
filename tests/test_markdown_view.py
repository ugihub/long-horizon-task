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
        self.assertIn(">>", md)  # active marker (ASCII)

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

    def test_pipe_in_title_is_escaped(self):
        state = dict(self.state)
        state["tasks"] = [
            {"id": "T01", "title": "a|b", "objective": "", "status": "active",
             "depends_on": [], "risk_level": "low", "allowed_paths": [], "allowed_commands": [],
             "definition_of_done": [], "artifacts": [], "evidence": [],
             "attempts": 0, "max_attempts": 3},
        ]
        md = self.view.render_tracker(state)
        self.assertIn(r"a\|b", md)

    def test_each_row_has_7_cells(self):
        md = self.view.render_tracker(self.state)
        for line in md.splitlines():
            if line.startswith("|") and not line.startswith("|----") and not line.startswith("| ID |"):
                # count unescaped pipes = 8 (7 cells)
                self.assertEqual(line.count("|"), 8, f"row malformed: {line}")

    def test_non_dict_task_skipped(self):
        state = dict(self.state)
        state["tasks"] = [None, "not a dict"]
        md = self.view.render_tracker(state)  # should not crash
        # header renders; non-dict tasks are skipped without producing a row
        self.assertIn("| ID |", md)
        self.assertNotIn("not a dict", md)

    def test_missing_field_task_uses_defaults(self):
        state = dict(self.state)
        state["tasks"] = [{"id": "T01"}]
        md = self.view.render_tracker(state)
        self.assertIn("T01", md)

    def test_redacts_secret_in_cell(self):
        from engine.lhtm.redactor import Redactor
        view = MarkdownView(redactor=Redactor())
        state = {
            "schema_version": "1.0", "run_id": "r", "goal": {"text": "g", "hash": "h"*64},
            "phase": "EXECUTING", "mode": "SUPERVISED", "active_task_id": None,
            "policy": {}, "current_step": 0,
            "tasks": [{
                "id": "T01", "title": "set token=abc123", "objective": "", "status": "active",
                "depends_on": [], "risk_level": "low", "allowed_paths": [],
                "allowed_commands": [], "definition_of_done": [], "artifacts": [],
                "evidence": [], "attempts": 0, "max_attempts": 3,
            }],
        }
        md = view.render_tracker(state)
        self.assertIn("[REDACTED]", md)
        self.assertNotIn("abc123", md)

if __name__ == "__main__":
    unittest.main()
