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
        errs = self.v.validate_update({"task_id": "T01", "status": "blocked"})
        self.assertEqual(errs, [])

    def test_validate_update_engine_owned_status(self):
        errs = self.v.validate_update({"task_id": "T01", "status": "verified_done"})
        self.assertTrue(any("LLM" in e or "engine" in e.lower() for e in errs))

    def test_validate_update_active_is_engine_owned(self):
        errs = self.v.validate_update({"task_id": "T01", "status": "active"})
        self.assertTrue(any("active" in e for e in errs))

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

    def test_claimed_done_requires_evidence(self):
        errs = self.v.validate_update({"task_id": "T01", "status": "claimed_done"})
        self.assertTrue(any("evidence" in e for e in errs))
        # with evidence it's fine
        errs = self.v.validate_update({"task_id": "T01", "status": "claimed_done", "evidence": [{"type": "test", "path": "x"}]})
        self.assertEqual(errs, [])

    def test_validate_state_checks_tasks(self):
        state = {
            "schema_version": "1.0", "run_id": "r", "goal": {"text": "g", "hash": "0" * 64},
            "phase": "DRAFT", "mode": "DRY_RUN", "active_task_id": None, "policy": {},
            "tasks": [{"no": "id"}], "current_step": 0,
        }
        errs = self.v.validate_state(state)
        self.assertTrue(any("missing field" in e for e in errs))

    def test_validate_plan_rejects_non_pending_initial(self):
        plan = {
            "schema_version": "1.0",
            "run_id": "test-123",
            "goal_hash": "x" * 64,
            "title": "Bad", "objective": "X",
            "tasks": [
                {"id": "T01", "title": "A", "objective": "", "status": "active",
                 "depends_on": [], "risk_level": "low", "allowed_paths": [],
                 "allowed_commands": [], "definition_of_done": [], "artifacts": [],
                 "evidence": [], "attempts": 0, "max_attempts": 3},
            ],
            "open_questions": [], "metadata": {}, "approved": False,
        }
        errs = self.v.validate_plan(plan)
        self.assertTrue(any("initial status must be 'pending'" in e for e in errs))

    def test_claimed_done_with_empty_evidence_rejected(self):
        errs = self.v.validate_update({"task_id": "T01", "status": "claimed_done", "evidence": []})
        self.assertTrue(any("evidence" in e for e in errs))

    def test_state_task_in_progress_status_passes(self):
        state = {
            "schema_version": "1.0", "run_id": "r", "goal": {"text": "g", "hash": "0" * 64},
            "phase": "EXECUTING", "mode": "DRY_RUN", "active_task_id": None, "policy": {},
            "tasks": [
                {"id": "T01", "title": "A", "objective": "", "status": "active",
                 "depends_on": [], "risk_level": "low", "allowed_paths": [],
                 "allowed_commands": [], "definition_of_done": [], "artifacts": [],
                 "evidence": [], "attempts": 0, "max_attempts": 3},
            ],
            "current_step": 0,
        }
        errs = self.v.validate_state(state)
        self.assertEqual(errs, [])

    def test_plan_with_missing_id_does_not_crash(self):
        plan = {
            "schema_version": "1.0",
            "run_id": "test-123",
            "goal_hash": "x" * 64,
            "title": "NoId", "objective": "X",
            "tasks": [{"depends_on": []}],
            "open_questions": [], "metadata": {}, "approved": False,
        }
        errs = self.v.validate_plan(plan)  # should not raise
        self.assertTrue(any("missing field" in e for e in errs))

    def test_validate_plan_duplicate_task_ids(self):
        plan = {
            "schema_version": "1.0",
            "run_id": "test-123",
            "goal_hash": "x" * 64,
            "title": "Dup", "objective": "X",
            "tasks": [
                {"id": "T01", "title": "A", "objective": "", "status": "pending",
                 "depends_on": [], "risk_level": "low", "allowed_paths": [],
                 "allowed_commands": [], "definition_of_done": [], "artifacts": [],
                 "evidence": [], "attempts": 0, "max_attempts": 3},
                {"id": "T01", "title": "B", "objective": "", "status": "pending",
                 "depends_on": [], "risk_level": "low", "allowed_paths": [],
                 "allowed_commands": [], "definition_of_done": [], "artifacts": [],
                 "evidence": [], "attempts": 0, "max_attempts": 3},
            ],
            "open_questions": [], "metadata": {}, "approved": False,
        }
        errs = self.v.validate_plan(plan)
        self.assertTrue(any("duplicate" in e for e in errs))

if __name__ == "__main__":
    unittest.main()
