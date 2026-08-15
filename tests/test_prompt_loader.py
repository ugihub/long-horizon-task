# tests/test_prompt_loader.py
import os, unittest
from engine.lhtm.prompt_loader import PromptLoader

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestPromptLoader(unittest.TestCase):
    def setUp(self):
        self.loader = PromptLoader(repo_root=REPO_ROOT)

    def test_load_executor_skill(self):
        text = self.loader.load("skills/executor/SKILL.md")
        self.assertIn("Executor Skill", text)

    def test_load_output_contract(self):
        text = self.loader.load("skills/output-contract/SKILL.md")
        self.assertIn("lhtm-update", text)

    def test_load_multiple(self):
        text = self.loader.load("skills/output-contract/SKILL.md", "skills/lhtm-core/SKILL.md")
        self.assertIn("lhtm-update", text)
        self.assertIn("10 Rules", text)

    def test_missing_file_returns_empty(self):
        text = self.loader.load("skills/does_not_exist.md")
        self.assertEqual(text, "")


if __name__ == "__main__":
    unittest.main()