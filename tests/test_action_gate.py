# tests/test_action_gate.py
import unittest
from engine.lhtm.action_gate import ActionGate
from engine.lhtm.config import DEFAULT_CONFIG


def make_task(tid="T01", allowed_paths=("src/", "README.md"), risk="low"):
    return {
        "id": tid, "title": "t", "objective": "", "status": "active",
        "depends_on": [], "risk_level": risk,
        "allowed_paths": list(allowed_paths),
        "allowed_commands": [], "definition_of_done": [], "artifacts": [],
        "evidence": [], "attempts": 0, "max_attempts": 3,
    }


class TestActionGate(unittest.TestCase):
    def setUp(self):
        self.gate = ActionGate()
        self.cfg = dict(DEFAULT_CONFIG)
        self.task = make_task()

    def check(self, action, task=None, mode="SUPERVISED", active="T01"):
        return self.gate.check(action, task or self.task, self.cfg, mode, active)

    def test_write_allowed_path_requires_approval(self):
        d = self.check({"action": "write_file", "path": "src/new.py", "content": "x"})
        self.assertTrue(d["allowed"])
        self.assertTrue(d["requires_approval"])

    def test_write_outside_allowed_path_rejected(self):
        d = self.check({"action": "write_file", "path": "../evil.py", "content": "x"})
        self.assertFalse(d["allowed"])
        self.assertIn("path", d["reason"].lower())

    def test_write_exact_file_allowed(self):
        d = self.check({"action": "write_file", "path": "README.md", "content": "x"})
        self.assertTrue(d["allowed"])

    def test_write_to_existing_file_needs_approval_in_auto_safe(self):
        import os, tempfile
        tmp = tempfile.mkdtemp()
        existing = os.path.join(tmp, "a.py")
        with open(existing, "w") as f:
            f.write("old")
        task = make_task(allowed_paths=(tmp + os.sep,))
        # AUTO_SAFE normally auto-allows writes, but existing-file overwrite still needs approval
        d = self.check({"action": "write_file", "path": existing, "content": "new"}, task=task, mode="AUTO_SAFE")
        self.assertTrue(d["allowed"])
        self.assertTrue(d["requires_approval"])

    def test_read_file_allowed_no_approval(self):
        d = self.check({"action": "read_file", "path": "src/a.py"})
        self.assertTrue(d["allowed"])
        self.assertFalse(d["requires_approval"])

    def test_read_sensitive_blocked(self):
        d = self.check({"action": "read_file", "path": ".env"})
        self.assertFalse(d["allowed"])
        self.assertIn("sensitiv", d["reason"].lower())

    def test_read_blocked_dir(self):
        d = self.check({"action": "read_file", "path": ".aws/credentials"})
        self.assertFalse(d["allowed"])

    def test_run_command_in_allowlist(self):
        d = self.check({"action": "run_command", "tool": "pytest", "args": ["-q"]})
        self.assertTrue(d["allowed"])
        self.assertTrue(d["requires_approval"])

    def test_run_command_not_in_allowlist(self):
        d = self.check({"action": "run_command", "tool": "rm", "args": ["-rf", "/"]})
        self.assertFalse(d["allowed"])

    def test_run_command_destructive_denied_even_if_allowlisted(self):
        cfg = dict(DEFAULT_CONFIG)
        cfg["allowed_commands"] = cfg["allowed_commands"] + ["sudo apt install"]
        d = self.gate.check({"action": "run_command", "tool": "sudo", "args": ["apt", "install", "x"]},
                            self.task, cfg, "SUPERVISED", "T01")
        self.assertFalse(d["allowed"])

    def test_delete_file_requires_approval(self):
        d = self.check({"action": "delete_file", "path": "src/a.py"})
        self.assertTrue(d["allowed"])
        self.assertTrue(d["requires_approval"])

    def test_delete_outside_path_rejected(self):
        d = self.check({"action": "delete_file", "path": "elsewhere.py"})
        self.assertFalse(d["allowed"])

    def test_unknown_action_rejected(self):
        d = self.check({"action": "exploit", "path": "src/a.py"})
        self.assertFalse(d["allowed"])

    def test_ask_user_allowed(self):
        d = self.check({"action": "ask_user", "question": "Proceed?"})
        self.assertTrue(d["allowed"])

    def test_active_task_mismatch_rejected(self):
        d = self.check({"action": "read_file", "path": "src/a.py"}, active="T99")
        self.assertFalse(d["allowed"])
        self.assertIn("active", d["reason"].lower())

    def test_full_auto_skips_approval_for_write(self):
        d = self.check({"action": "write_file", "path": "src/new.py", "content": "x"}, mode="FULL_AUTO")
        self.assertTrue(d["allowed"])
        self.assertFalse(d["requires_approval"])

    def test_sensitive_beats_allowed_path(self):
        # path IS within allowed_paths but also sensitive -> rejected always
        d = self.check({"action": "read_file", "path": "src/.env"})
        self.assertFalse(d["allowed"])

    def test_unknown_mode_fails_closed(self):
        # any mode other than FULL_AUTO must require approval for writes
        d = self.check({"action": "write_file", "path": "src/new.py", "content": "x"}, mode="INJECTED")
        self.assertTrue(d["allowed"])
        self.assertTrue(d["requires_approval"])

    def test_run_command_bad_args_type_rejected(self):
        # args must be a list; None/non-list must not crash the gate
        d = self.check({"action": "run_command", "tool": "pytest", "args": None})
        self.assertFalse(d["allowed"])

    def test_run_command_space_anchor_prevents_prefix_escape(self):
        # allowlist "pytest" must not match a different tool whose name merely starts with it
        d = self.check({"action": "run_command", "tool": "pytestx", "args": ["-q"]})
        self.assertFalse(d["allowed"])


if __name__ == "__main__":
    unittest.main()
