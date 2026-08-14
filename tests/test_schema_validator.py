# tests/test_schema_validator.py
import unittest
from engine.lhtm.schema_validator import SchemaValidator
from engine.lhtm.goal_hash import GoalHash

class TestSchemaValidator(unittest.TestCase):
    def setUp(self):
        self.v = SchemaValidator()
        self.valid_state = {
            "schema_version": "1.0",
            "run_id": "test-123",
            "goal": GoalHash.freeze("test"),
            "phase": "DRAFT",
            "mode": "DRY_RUN",
            "active_task_id": None,
            "policy": {},
            "tasks": [],
            "current_step": 0,
        }

    def test_valid_state_returns_empty(self):
        errs = self.v.validate_state(self.valid_state)
        self.assertEqual(errs, [])

    def test_invalid_schema_version(self):
        state = dict(self.valid_state, schema_version="0.5")
        errs = self.v.validate_state(state)
        self.assertTrue(any("schema_version" in e for e in errs))

    def test_invalid_phase(self):
        state = dict(self.valid_state, phase="NONSENSE")
        errs = self.v.validate_state(state)
        self.assertTrue(any("phase" in e for e in errs))

    def test_invalid_mode(self):
        state = dict(self.valid_state, mode="UNSAFE")
        errs = self.v.validate_state(state)
        self.assertTrue(any("mode" in e for e in errs))

    def test_validate_plan_valid(self):
        plan = {
            "schema_version": "1.0",
            "run_id": "test-123",
            "goal_hash": GoalHash.freeze("test")["hash"],
            "title": "Plan",
            "objective": "Do stuff",
            "tasks": [
                {"id": "T01", "title": "Task 1", "objective": "A", "status": "pending",
                 "depends_on": [], "risk_level": "low", "allowed_paths": [],
                 "allowed_commands": [], "definition_of_done": [], "artifacts": [],
                 "evidence": [], "attempts": 0, "max_attempts": 3},
                {"id": "T02", "title": "Task 2", "objective": "B", "status": "pending",
                 "depends_on": ["T01"], "risk_level": "low", "allowed_paths": [],
                 "allowed_commands": [], "definition_of_done": [], "artifacts": [],
                 "evidence": [], "attempts": 0, "max_attempts": 3},
            ],
            "open_questions": [],
            "metadata": {"model": "test", "generated_at": "now", "generator": "test"},
            "approved": False,
        }
        errs = self.v.validate_plan(plan)
        self.assertEqual(errs, [])

    def test_plan_cyclic_dependency(self):
        plan = {
            "schema_version": "1.0",
            "run_id": "test-123",
            "goal_hash": "x"*64,
            "title": "Cyclic",
            "objective": "X",
            "tasks": [
                {"id": "T01", "title": "A", "objective": "", "status": "pending",
                 "depends_on": ["T02"], "risk_level": "low", "allowed_paths": [],
                 "allowed_commands": [], "definition_of_done": [], "artifacts": [],
                 "evidence": [], "attempts": 0, "max_attempts": 3},
                {"id": "T02", "title": "B", "objective": "", "status": "pending",
                 "depends_on": ["T01"], "risk_level": "low", "allowed_paths": [],
                 "allowed_commands": [], "definition_of_done": [], "artifacts": [],
                 "evidence": [], "attempts": 0, "max_attempts": 3},
            ],
            "open_questions": [],
            "metadata": {},
            "approved": False,
        }
        errs = self.v.validate_plan(plan)
        self.assertTrue(any("cyclic" in e.lower() for e in errs))

    def test_plan_missing_dep(self):
        plan = {
            "schema_version": "1.0",
            "run_id": "test-123",
            "goal_hash": "x"*64,
            "title": "Bad",
            "objective": "X",
            "tasks": [
                {"id": "T01", "title": "A", "objective": "", "status": "pending",
                 "depends_on": ["T99"], "risk_level": "low", "allowed_paths": [],
                 "allowed_commands": [], "definition_of_done": [], "artifacts": [],
                 "evidence": [], "attempts": 0, "max_attempts": 3},
            ],
            "open_questions": [],
            "metadata": {},
            "approved": False,
        }
        errs = self.v.validate_plan(plan)
        self.assertTrue(any("T99" in e for e in errs))

    def test_validate_update_legal(self):
        errs = self.v.validate_update({"task_id": "T01", "status": "claimed_done"})
        self.assertEqual(errs, [])

    def test_validate_update_engine_owned_status(self):
        errs = self.v.validate_update({"task_id": "T01", "status": "verified_done"})
        self.assertTrue(any("LLM" in e or "engine" in e.lower() for e in errs))

    def test_validate_update_invalid_status(self):
        errs = self.v.validate_update({"task_id": "T01", "status": "nonsense"})
        self.assertTrue(any("status" in e for e in errs))

    def test_illegal_transition(self):
        errs = self.v.validate_transition("pending", "active")
        self.assertTrue(errs)

    def test_legal_transition(self):
        errs = self.v.validate_transition("pending", "ready")
        self.assertEqual(errs, [])

    def test_illegal_phase_transition(self):
        errs = self.v.validate_phase_transition("COMPLETED", "EXECUTING")
        self.assertTrue(errs)

    def test_legal_phase_transition(self):
        errs = self.v.validate_phase_transition("DRAFT", "PLANNING")
        self.assertEqual(errs, [])

    def test_legal_recovery_phase_transition(self):
        errs = self.v.validate_phase_transition("EXECUTING", "BLOCKED")
        self.assertEqual(errs, [])

if __name__ == "__main__":
    unittest.main()
