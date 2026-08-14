# tests/test_audit.py
import json, os, tempfile, shutil, unittest
from engine.lhtm.audit import AuditLogger


class TestAudit(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.path = os.path.join(self.tmp, "events.jsonl")
        self.audit = AuditLogger(self.path)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_log_writes_json_line(self):
        self.audit.log({"event": "action_executed", "action": "write_file", "result": "ok"})
        with open(self.path, encoding="utf-8") as f:
            lines = f.read().strip().splitlines()
        self.assertEqual(len(lines), 1)
        data = json.loads(lines[0])
        self.assertEqual(data["action"], "write_file")
        self.assertIn("ts", data)

    def test_log_step_writes_structured_fields(self):
        self.audit.log_step(run_id="r1", phase="EXECUTING", active_task_id="T01",
                            action="run_command", result="ok", duration_ms=12)
        with open(self.path, encoding="utf-8") as f:
            data = json.loads(f.readline())
        self.assertEqual(data["event"], "step")
        self.assertEqual(data["run_id"], "r1")
        self.assertEqual(data["active_task_id"], "T01")
        self.assertEqual(data["duration_ms"], 12)


if __name__ == "__main__":
    unittest.main()
