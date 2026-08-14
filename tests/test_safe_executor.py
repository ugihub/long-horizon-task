# tests/test_safe_executor.py
import os, tempfile, shutil, unittest
from engine.lhtm.safe_executor import SafeExecutor
from engine.lhtm.config import DEFAULT_CONFIG


def approved(decision):
    return {**decision, "allowed": True, "requires_approval": False}


class TestSafeExecutor(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.cfg = dict(DEFAULT_CONFIG)
        self.exe = SafeExecutor(self.cfg)
        self.src = os.path.join(self.tmp, "src")
        os.makedirs(self.src, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_write_file_creates_file(self):
        path = os.path.join(self.src, "a.py")
        r = self.exe.execute({"action": "write_file", "path": path, "content": "x = 1"},
                             approved({"allowed": True}), {})
        self.assertTrue(r["ok"])
        with open(path, encoding="utf-8") as f:
            self.assertEqual(f.read(), "x = 1")

    def test_write_refuses_unapproved_decision(self):
        r = self.exe.execute({"action": "write_file", "path": os.path.join(self.src, "b.py"), "content": "x"},
                             {"allowed": True, "requires_approval": True}, {})
        self.assertFalse(r["ok"])
        self.assertIn("approval", r["error"].lower())

    def test_write_refuses_not_allowed(self):
        r = self.exe.execute({"action": "write_file", "path": os.path.join(self.src, "c.py"), "content": "x"},
                             {"allowed": False, "reason": "nope"}, {})
        self.assertFalse(r["ok"])

    def test_write_backs_up_existing_file(self):
        path = os.path.join(self.src, "d.py")
        with open(path, "w", encoding="utf-8") as f:
            f.write("old")
        r = self.exe.execute({"action": "write_file", "path": path, "content": "new"},
                             approved({"allowed": True}), {})
        self.assertTrue(r["ok"])
        with open(path, encoding="utf-8") as f:
            self.assertEqual(f.read(), "new")
        # a .bak exists
        baks = [x for x in os.listdir(self.src) if x.endswith(".bak")]
        self.assertEqual(len(baks), 1)

    def test_read_file_returns_content(self):
        path = os.path.join(self.src, "r.py")
        with open(path, "w", encoding="utf-8") as f:
            f.write("hello")
        r = self.exe.execute({"action": "read_file", "path": path}, approved({"allowed": True}), {})
        self.assertTrue(r["ok"])
        self.assertEqual(r["result"], "hello")

    def test_delete_file_moves_to_trash(self):
        path = os.path.join(self.src, "del.py")
        with open(path, "w", encoding="utf-8") as f:
            f.write("x")
        r = self.exe.execute({"action": "delete_file", "path": path}, approved({"allowed": True}), {})
        self.assertTrue(r["ok"])
        self.assertFalse(os.path.exists(path))
        trash = os.path.join(self.tmp, ".trash")
        self.assertTrue(os.path.exists(trash))
        self.assertEqual(len(os.listdir(trash)), 1)

    def test_run_command_executes_and_returns_stdout(self):
        r = self.exe.execute({"action": "run_command", "tool": "python", "args": ["-c", "print('ok')"]},
                             approved({"allowed": True}), {})
        self.assertTrue(r["ok"])
        self.assertIn("ok", r["result"])

    def test_run_command_captures_failure(self):
        r = self.exe.execute({"action": "run_command", "tool": "python", "args": ["-c", "import sys; sys.exit(3)"]},
                             approved({"allowed": True}), {})
        self.assertFalse(r["ok"])
        self.assertIn("exit", r["error"].lower())

    def test_run_command_summarizes_long_output(self):
        big = "x" * 5000
        self.cfg["limits"]["max_log_chars_sent_to_model"] = 100
        self.exe = SafeExecutor(self.cfg)
        r = self.exe.execute({"action": "run_command", "tool": "python", "args": ["-c", f"print('{big}')"]},
                             approved({"allowed": True}), {})
        self.assertTrue(r["ok"])
        self.assertLessEqual(len(r["result"]), 150)

    def test_unknown_action_returns_error(self):
        r = self.exe.execute({"action": "exploit"}, approved({"allowed": True}), {})
        self.assertFalse(r["ok"])


if __name__ == "__main__":
    unittest.main()
