# tests/test_release_ci.py
import os
import sys
import unittest

import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WF = os.path.join(ROOT, ".github", "workflows")
WORKFLOWS = ("test.yml", "lint.yml", "eval.yml")


class TestReleaseCi(unittest.TestCase):
    def test_workflows_exist(self):
        for name in WORKFLOWS:
            self.assertTrue(os.path.isfile(os.path.join(WF, name)), f"missing {name}")

    def test_workflows_parse_and_have_jobs(self):
        for name in WORKFLOWS:
            with open(os.path.join(WF, name), encoding="utf-8") as f:
                data = yaml.safe_load(f)
            self.assertIsInstance(data, dict, name)
            self.assertIn("name", data, name)
            # PyYAML 1.1 parses the `on:` trigger key as boolean True
            self.assertTrue(("on" in data) or (True in data), f"{name}: missing on trigger")
            self.assertIn("jobs", data, name)
            self.assertTrue(data["jobs"], f"{name}: no jobs")


if __name__ == "__main__":
    unittest.main()
