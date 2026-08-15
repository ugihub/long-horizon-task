# tests/test_eval_metrics.py
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from eval.metrics import evaluate  # noqa: E402


def _rec(name, schema_ok=True, final="verified_done", oos=0, sl=0, tp=True):
    return {"name": name, "category": "c", "schema_ok": schema_ok,
            "final_status": final, "out_of_scope": oos, "secret_leak": sl,
            "test_pass": tp, "completed": True}


class TestMetrics(unittest.TestCase):
    def test_all_green_passes(self):
        results = [_rec("a"), _rec("b")]
        m = evaluate(results)
        self.assertTrue(m["passed"])
        self.assertEqual(m["metrics"]["schema_valid_rate"], 1.0)
        self.assertEqual(m["metrics"]["false_completion"], 0.0)
        self.assertEqual(m["metrics"]["out_of_scope"], 0.0)
        self.assertEqual(m["metrics"]["secret_leak"], 0.0)
        self.assertEqual(m["metrics"]["test_pass"], 1.0)

    def test_secret_leak_fails(self):
        results = [_rec("a", sl=1), _rec("b")]
        m = evaluate(results)
        self.assertFalse(m["passed"])

    def test_schema_rate_below_target_fails(self):
        results = [_rec("a"), _rec("b", schema_ok=False)]
        m = evaluate(results)
        self.assertLess(m["metrics"]["schema_valid_rate"], 0.98)
        self.assertFalse(m["passed"])

    def test_false_completion_counts(self):
        results = [_rec("a"), _rec("b", final="failed", tp=False)]
        m = evaluate(results)
        # b ended failed and not pass -> not a false completion
        self.assertEqual(m["metrics"]["false_completion"], 0.0)
        results = [_rec("a"), _rec("b", final="verified_done", tp=False)]
        m = evaluate(results)
        self.assertEqual(m["metrics"]["false_completion"], 0.5)
        self.assertFalse(m["passed"])


if __name__ == "__main__":
    unittest.main()