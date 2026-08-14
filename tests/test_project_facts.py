# tests/test_project_facts.py
import os, tempfile, shutil, unittest
from engine.lhtm.project_facts import ProjectFacts
from engine.lhtm.config import DEFAULT_CONFIG


class TestProjectFacts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.cfg = dict(DEFAULT_CONFIG)
        os.makedirs(os.path.join(self.tmp, "src"), exist_ok=True)
        with open(os.path.join(self.tmp, "src", "a.py"), "w", encoding="utf-8") as f:
            f.write("x = 1\n" * 5)
        with open(os.path.join(self.tmp, "src", "b.py"), "w", encoding="utf-8") as f:
            f.write("y = 2")
        with open(os.path.join(self.tmp, "src", ".env"), "w", encoding="utf-8") as f:
            f.write("SECRET=1")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _facts(self):
        return ProjectFacts(self.tmp, self.cfg)

    def test_scan_respects_allowed_paths(self):
        facts = self._facts().scan(["src/"])
        paths = {f["path"] for f in facts["files"]}
        self.assertIn("src/a.py", paths)
        self.assertNotIn("src/.env", paths)  # blocked

    def test_scan_excludes_blocked(self):
        facts = self._facts().scan(["."])
        paths = {f["path"] for f in facts["files"]}
        self.assertNotIn("src/.env", paths)
        self.assertIn("src/a.py", paths)

    def test_summary_capped(self):
        cfg = dict(self.cfg)
        cfg["limits"]["max_facts_chars"] = 10
        f = ProjectFacts(self.tmp, cfg).scan(["src/"])
        self.assertLessEqual(len(f["summary"]), 40)

    def test_excerpts_read_top_files(self):
        ex = self._facts().excerpts(["src/"], n=1, max_chars=50)
        self.assertEqual(len(ex), 1)
        self.assertIn("x = 1", ex[0])

    def test_render_md(self):
        md = self._facts().render(["src/"])
        self.assertIn("# LHTM Project Facts", md)
        self.assertIn("src/a.py", md)

    def test_empty_dir(self):
        empty = os.path.join(self.tmp, "empty")
        os.makedirs(empty, exist_ok=True)
        f = ProjectFacts(self.tmp, self.cfg).scan([empty])
        self.assertEqual(f["files"], [])


if __name__ == "__main__":
    unittest.main()
