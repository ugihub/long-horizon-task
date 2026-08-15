# tests/test_eval_report.py
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from eval.report import render_report  # noqa: E402


class TestEvalReport(unittest.TestCase):
    def test_render_includes_sections(self):
        results = [
            {"name": "a", "category": "c1", "schema_ok": True,
             "final_status": "verified_done", "out_of_scope": 0,
             "secret_leak": 0, "test_pass": True, "completed": True},
        ]
        metrics = {"schema_valid_rate": 1.0, "false_completion": 0.0,
                   "out_of_scope": 0.0, "secret_leak": 0.0, "test_pass": 1.0}
        md = render_report(results, metrics, passed=True)
        self.assertIn("# P8 Evaluation Report", md)
        self.assertIn("schema_valid_rate", md)
        self.assertIn("category", md.lower())
        self.assertIn("PASS", md)

    def test_render_fail_line(self):
        metrics = {"schema_valid_rate": 0.5, "false_completion": 0.0,
                   "out_of_scope": 0.0, "secret_leak": 0.0, "test_pass": 1.0}
        md = render_report([], metrics, passed=False)
        self.assertIn("FAIL", md)


if __name__ == "__main__":
    unittest.main()