# tests/test_skills.py
import os
import sys
import unittest

import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = os.path.join(ROOT, "skills")
EXPECTED = {"lhtm-core", "planner", "executor", "verifier", "recovery", "output-contract"}


def _frontmatter(path):
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    if lines[:1] != ["---"]:
        return None
    end = lines[1:].index("---") + 1
    return yaml.safe_load("\n".join(lines[1:end]))


class TestSkills(unittest.TestCase):
    def test_six_skill_dirs(self):
        dirs = {d for d in os.listdir(SKILLS) if os.path.isdir(os.path.join(SKILLS, d))}
        self.assertEqual(dirs, EXPECTED)

    def test_each_skill_has_valid_frontmatter(self):
        for name in EXPECTED:
            p = os.path.join(SKILLS, name, "SKILL.md")
            self.assertTrue(os.path.isfile(p), f"{name}: SKILL.md missing")
            fm = _frontmatter(p)
            self.assertIsNotNone(fm, f"{name}: missing frontmatter")
            self.assertIn("name", fm, f"{name}: missing name")
            self.assertIn("description", fm, f"{name}: missing description")
            self.assertEqual(fm["name"], name, f"{name}: frontmatter name mismatch")
            self.assertIsInstance(fm["description"], str)
            self.assertTrue(fm["description"].strip(), f"{name}: empty description")


if __name__ == "__main__":
    unittest.main()
