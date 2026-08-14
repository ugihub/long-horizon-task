# tests/test_runbook.py
import copy, os, tempfile, shutil, unittest
from engine.lhtm.runbook import RunbookRunner
from engine.lhtm.config import DEFAULT_CONFIG


def make_runbook(title="rb", steps=None):
    return {"runbook_version": 1, "title": title, "description": "",
            "steps": steps if steps is not None else []}


class TestRunbook(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.cfg = copy.deepcopy(DEFAULT_CONFIG)
        self.rb = RunbookRunner(self.cfg)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_validate_ok(self):
        rb = make_runbook(steps=[{"id": "s1", "action": "run_command", "tool": "python", "args": ["-c", "print('ok')"]}])
        self.assertEqual(self.rb.validate(rb), [])

    def test_validate_missing_id(self):
        rb = make_runbook(steps=[{"action": "run_command", "tool": "python", "args": []}])
        errs = self.rb.validate(rb)
        self.assertTrue(any("missing" in e for e in errs))

    def test_validate_bad_action(self):
        rb = make_runbook(steps=[{"id": "s1", "action": "rm"}])
        errs = self.rb.validate(rb)
        self.assertTrue(any("invalid action" in e for e in errs))

    def test_run_command_step(self):
        rb = make_runbook(steps=[{"id": "s1", "action": "run_command", "tool": "python",
                                  "args": ["-c", "print('hello runbook')"]}])
        r = self.rb.execute(rb, self.tmp, self.cfg)
        self.assertTrue(r["ok"])
        self.assertIn("hello runbook", r["steps"][0]["result"])

    def test_write_file_creates_and_backs_up(self):
        path = os.path.join(self.tmp, "src", "x.py")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write("old")
        rb = make_runbook(steps=[{"id": "w1", "action": "write_file", "path": "src/x.py", "content": "new"}])
        r = self.rb.execute(rb, self.tmp, self.cfg)
        self.assertTrue(r["ok"])
        with open(path, encoding="utf-8") as f:
            self.assertEqual(f.read(), "new")
        baks = [x for x in os.listdir(os.path.dirname(path)) if x.endswith(".bak")]
        self.assertEqual(len(baks), 1)

    def test_assert_contains(self):
        path = os.path.join(self.tmp, "a.py")
        with open(path, "w", encoding="utf-8") as f:
            f.write("def main():\n    pass")
        rb = make_runbook(steps=[{"id": "a1", "action": "assert", "path": "a.py", "contains": "def main"}])
        r = self.rb.execute(rb, self.tmp, self.cfg)
        self.assertTrue(r["ok"])

    def test_assert_missing_file_fails(self):
        rb = make_runbook(steps=[{"id": "a1", "action": "assert", "path": "nope.py", "contains": "x"}])
        r = self.rb.execute(rb, self.tmp, self.cfg)
        self.assertFalse(r["ok"])
        self.assertIn("missing", r["error"])

    def test_stop_on_failure(self):
        rb = make_runbook(steps=[
            {"id": "s1", "action": "run_command", "tool": "python", "args": ["-c", "import sys; sys.exit(1)"]},
            {"id": "s2", "action": "assert", "path": "never.py", "contains": "x"},
        ])
        r = self.rb.execute(rb, self.tmp, self.cfg)
        self.assertFalse(r["ok"])
        self.assertEqual(len(r["steps"]), 1)  # second step not executed

    def test_dry_run_writes_nothing(self):
        rb = make_runbook(steps=[{"id": "w1", "action": "write_file", "path": "src/x.py", "content": "new"}])
        r = self.rb.execute(rb, self.tmp, self.cfg, dry_run=True)
        self.assertTrue(r["ok"])
        self.assertTrue(r["steps"][0]["dry_run"])
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "src", "x.py")))

    def test_idempotent_skips_done(self):
        rb = make_runbook(steps=[{"id": "s1", "action": "run_command", "tool": "python",
                                  "args": ["-c", "print('run once')"]}])
        self.rb.execute(rb, self.tmp, self.cfg)
        r = self.rb.execute(rb, self.tmp, self.cfg)
        self.assertTrue(r["ok"])
        self.assertTrue(r["steps"][0].get("skipped"))


if __name__ == "__main__":
    unittest.main()
