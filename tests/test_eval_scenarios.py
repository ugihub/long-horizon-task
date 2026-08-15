# tests/test_eval_scenarios.py
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from eval import scenarios  # noqa: E402


FIXTURES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "eval", "fixtures")


def _load(name, category):
    p = os.path.join(FIXTURES, category, name)
    with open(p, encoding="utf-8") as f:
        return json.load(f)


class TestScenarios(unittest.TestCase):
    def test_load_fixtures_finds_seed(self):
        names = {fx["name"] for fx in scenarios.load_fixtures(FIXTURES)}
        self.assertIn("linear_ok", names)
        self.assertIn("write_outside_allowed", names)

    def test_linear_ok_record(self):
        fx = _load("01_linear_ok.json", "category_01_linear")
        rec = scenarios.run_scenario(fx)
        self.assertTrue(rec["schema_ok"])
        self.assertEqual(rec["final_status"], "verified_done")
        self.assertEqual(rec["out_of_scope"], 0)
        self.assertEqual(rec["secret_leak"], 0)
        self.assertTrue(rec["test_pass"])
        self.assertTrue(rec["completed"])

    def test_out_of_scope_write_counted(self):
        fx = _load("01_write_outside_allowed.json", "category_07_out_of_scope")
        rec = scenarios.run_scenario(fx)
        self.assertEqual(rec["out_of_scope"], 1)
        # the in-scope write still happened, so verification passes
        self.assertEqual(rec["final_status"], "verified_done")
        self.assertTrue(rec["test_pass"])

    def test_run_scenario_uses_temp_workdir(self):
        fx = _load("01_linear_ok.json", "category_01_linear")
        prev = os.getcwd()
        with tempfile.TemporaryDirectory(prefix="lhtm-test-") as workdir:
            rec = scenarios.run_scenario(fx, workdir)
            self.assertIsNotNone(rec["name"])
            self.assertEqual(os.getcwd(), prev)
            self.assertTrue(os.path.exists(os.path.join(workdir, "src", "cli.py")))


    def test_recover_retry_ends_verified(self):
        fx = _load("01_recover_retry.json", "category_05_recovery")
        rec = scenarios.run_scenario(fx)
        self.assertTrue(rec["schema_ok"])
        self.assertEqual(rec["final_status"], "verified_done")
        self.assertTrue(rec["test_pass"])
        self.assertTrue(rec["completed"])

    def test_write_env_secret_counted(self):
        fx = _load("01_write_env.json", "category_06_secret_leak")
        rec = scenarios.run_scenario(fx)
        self.assertEqual(rec["secret_leak"], 1)
        self.assertEqual(rec["out_of_scope"], 0)
        self.assertTrue(rec["expected_ok"])
        self.assertEqual(rec["final_status"], "verified_done")

    def test_adversarial_fixtures_match_expected(self):
        for name, cat in (("01_rm_rf.json", "category_08_destructive"),
                          ("01_fake_evidence.json", "category_04_verify_fail"),
                          ("01_write_env.json", "category_06_secret_leak")):
            fx = _load(name, cat)
            rec = scenarios.run_scenario(fx)
            self.assertTrue(rec["expected_ok"], f"{fx['name']} diverged from expected")


if __name__ == "__main__":
    unittest.main()
