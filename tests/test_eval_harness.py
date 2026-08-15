# tests/test_eval_harness.py
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from eval.harness import EvalHarness  # noqa: E402


FIXTURES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "eval", "fixtures")


class TestEvalHarness(unittest.TestCase):
    def test_run_returns_report_shape(self):
        h = EvalHarness(FIXTURES)
        out = h.run()
        self.assertIn("results", out)
        self.assertIn("metrics", out)
        self.assertIn("passed", out)
        n_fixtures = sum(1 for _, _, files in os.walk(FIXTURES)
                         for fn in files if fn.endswith(".json"))
        self.assertEqual(len(out["results"]), n_fixtures)
        self.assertIsInstance(out["metrics"], dict)

    def test_run_is_deterministic_order(self):
        h = EvalHarness(FIXTURES)
        names_a = [r["name"] for r in h.run()["results"]]
        names_b = [r["name"] for r in h.run()["results"]]
        self.assertEqual(names_a, names_b)


if __name__ == "__main__":
    unittest.main()