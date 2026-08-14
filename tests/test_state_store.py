# tests/test_state_store.py
import unittest, os, json, tempfile, time
from pathlib import Path
from engine.lhtm.state_store import StateStore
from engine.lhtm.goal_hash import GoalHash

class TestStateStore(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.store = StateStore(self.tmpdir)
        self.sample = {
            "schema_version": "1.0",
            "run_id": "test-123",
            "goal": GoalHash.freeze("test goal"),
            "phase": "DRAFT",
            "mode": "DRY_RUN",
            "active_task_id": None,
            "policy": {},
            "tasks": [],
            "current_step": 0,
        }

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_save_and_load_roundtrip(self):
        self.store.save_state(self.sample)
        loaded = self.store.load_state()
        self.assertEqual(loaded["run_id"], "test-123")
        self.assertEqual(loaded["goal"]["text"], "test goal")

    def test_load_returns_new_state_if_no_file(self):
        loaded = self.store.load_state()
        self.assertIn("run_id", loaded)
        self.assertEqual(loaded["mode"], "DRY_RUN")

    def test_load_raises_on_corrupt_json(self):
        Path(self.store.state_path).write_text("{bad json")
        with self.assertRaises(json.JSONDecodeError):
            self.store.load_state()

    def test_lock_prevents_concurrent_access(self):
        self.store.acquire_lock()
        store2 = StateStore(self.tmpdir)
        self.assertFalse(store2.acquire_lock(blocking=False))
        self.store.release_lock()

    def test_snapshot_and_restore(self):
        self.store.save_state(self.sample)
        snap = self.store.create_snapshot()
        self.assertTrue(os.path.exists(snap))
        self.sample["phase"] = "EXECUTING"
        self.store.save_state(self.sample)
        self.store.restore_snapshot(snap)
        loaded = self.store.load_state()
        self.assertEqual(loaded["phase"], "DRAFT")

    def test_goal_hash_check_on_load(self):
        self.store.save_state(self.sample)
        # tamper the saved file
        state = json.loads(self.store.state_path.read_text())
        state["goal"]["hash"] = "0" * 64
        self.store.state_path.write_text(json.dumps(state))
        with self.assertRaises(ValueError):
            self.store.load_state()

if __name__ == "__main__":
    unittest.main()
