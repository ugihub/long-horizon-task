# tests/test_constants.py
import unittest
from engine.lhtm import constants as c


class TestConstants(unittest.TestCase):
    def test_phases_are_12(self):
        self.assertEqual(len(c.PHASES), 12)
        # all phases are unique
        self.assertEqual(len(set(c.PHASES)), 12)

    def test_phase_index_covers_all(self):
        self.assertEqual(set(c.PHASE_INDEX.keys()), set(c.PHASES))
        self.assertEqual(list(c.PHASE_INDEX.values()), list(range(12)))

    def test_statuses_are_8_and_unique(self):
        self.assertEqual(len(c.TASK_STATUSES), 8)
        self.assertEqual(len(set(c.TASK_STATUSES)), 8)

    def test_transition_keys_and_values_are_valid_statuses(self):
        for src, targets in c.LEGAL_TASK_TRANSITIONS.items():
            self.assertIn(src, c.TASK_STATUSES)
            for tgt in targets:
                self.assertIn(tgt, c.TASK_STATUSES)

    def test_terminal_statuses_have_no_targets(self):
        self.assertEqual(c.LEGAL_TASK_TRANSITIONS["verified_done"], set())
        self.assertEqual(c.LEGAL_TASK_TRANSITIONS["skipped"], set())

    def test_engine_owned_are_subset_of_statuses(self):
        self.assertTrue(c.ENGINE_OWNED_STATUSES <= set(c.TASK_STATUSES))
        # LLM-writable and engine-owned are disjoint and cover the statuses
        self.assertEqual(c.LLM_WRITABLE_STATUSES & c.ENGINE_OWNED_STATUSES, set())
        self.assertEqual(
            c.LLM_WRITABLE_STATUSES | c.ENGINE_OWNED_STATUSES, set(c.TASK_STATUSES)
        )

    def test_legal_phase_transition_forward(self):
        self.assertTrue(c.is_legal_phase_transition("DRAFT", "PLANNING"))
        self.assertTrue(c.is_legal_phase_transition("PLANNING", "PLAN_REVIEW"))
        self.assertTrue(c.is_legal_phase_transition("PLAN_REVIEW", "READY"))

    def test_illegal_phase_transition_backward(self):
        self.assertFalse(c.is_legal_phase_transition("COMPLETED", "EXECUTING"))
        self.assertFalse(c.is_legal_phase_transition("READY", "DRAFT"))

    def test_legal_phase_transition_recovery(self):
        # any phase may move to a recovery sink
        self.assertTrue(c.is_legal_phase_transition("EXECUTING", "BLOCKED"))
        self.assertTrue(c.is_legal_phase_transition("READY", "FAILED"))
        self.assertTrue(c.is_legal_phase_transition("PLANNING", "ABORTED"))

    def test_illegal_recovery_from_recovery_sink(self):
        # COMPLETED/ABORTED are terminals — no exit
        self.assertFalse(c.is_legal_phase_transition("ABORTED", "READY"))
        self.assertFalse(c.is_legal_phase_transition("COMPLETED", "READY"))

    def test_terminal_cannot_exit_to_any_recovery_sink(self):
        # terminals are absolute — even recovery sinks are unreachable
        self.assertFalse(c.is_legal_phase_transition("COMPLETED", "ABORTED"))
        self.assertFalse(c.is_legal_phase_transition("COMPLETED", "BLOCKED"))
        self.assertFalse(c.is_legal_phase_transition("COMPLETED", "FAILED"))
        self.assertFalse(c.is_legal_phase_transition("ABORTED", "RECOVERY"))

    def test_unknown_phase_illegal(self):
        self.assertFalse(c.is_legal_phase_transition("NONSENSE", "READY"))
        self.assertFalse(c.is_legal_phase_transition("DRAFT", "NONSENSE"))

    def test_modes(self):
        self.assertEqual(c.EXECUTION_MODES, ["DRY_RUN", "SUPERVISED", "AUTO_SAFE", "FULL_AUTO"])

    def test_default_policy(self):
        self.assertEqual(c.DEFAULT_POLICY["max_attempts"], 3)
        self.assertEqual(c.DEFAULT_POLICY["max_repair_attempts"], 2)


if __name__ == "__main__":
    unittest.main()
