# tests/test_goal_hash.py
import unittest
from engine.lhtm.goal_hash import GoalHash

class TestGoalHash(unittest.TestCase):
    def test_freeze_and_check(self):
        gh = GoalHash()
        state = gh.freeze("Build a todo app")
        self.assertIn("hash", state)
        self.assertIn("text", state)
        self.assertIn("frozen_at", state)
        self.assertEqual(state["text"], "Build a todo app")
        self.assertEqual(len(state["hash"]), 64)  # sha256 hex

    def test_check_ok(self):
        gh = GoalHash()
        state = gh.freeze("Build a todo app")
        gh.check(state)  # should not raise

    def test_check_mismatch_raises(self):
        gh = GoalHash()
        state = gh.freeze("Build a todo app")
        state["hash"] = "0" * 64
        with self.assertRaises(ValueError) as ctx:
            gh.check(state)
        self.assertIn("goal mismatch", str(ctx.exception).lower())

    def test_check_missing_hash_raises(self):
        gh = GoalHash()
        with self.assertRaises(ValueError):
            gh.check({})

    def test_check_one_key_only_raises(self):
        gh = GoalHash()
        with self.assertRaises(ValueError):
            gh.check({"hash": "0" * 64})
        with self.assertRaises(ValueError):
            gh.check({"text": "Build a todo app"})

    def test_check_non_dict_raises(self):
        gh = GoalHash()
        with self.assertRaises(ValueError):
            gh.check(None)

    def test_empty_goal_freezes_and_checks(self):
        gh = GoalHash()
        state = gh.freeze("")
        gh.check(state)  # should not raise

if __name__ == "__main__":
    unittest.main()
