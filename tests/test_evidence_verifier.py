# tests/test_evidence_verifier.py
import os, tempfile, shutil, unittest
from engine.lhtm.evidence_verifier import EvidenceVerifier


def make_task(**kw):
    t = {
        "id": "T01", "title": "t", "objective": "", "status": "claimed_done",
        "depends_on": [], "risk_level": "low", "allowed_paths": [],
        "allowed_commands": [], "definition_of_done": [], "artifacts": [],
        "evidence": [], "attempts": 0, "max_attempts": 3,
    }
    t.update(kw)
    return t


class TestEvidenceVerifier(unittest.TestCase):
    def setUp(self):
        self.v = EvidenceVerifier()
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _abs(self, name):
        return os.path.join(self.tmp, name)

    def _state(self, task):
        return {"schema_version": "1.0", "run_id": "r", "goal": {"text": "g", "hash": "h"*64},
                "phase": "EXECUTING", "mode": "SUPERVISED", "active_task_id": "T01",
                "policy": {}, "tasks": [task], "current_step": 0}

    def test_pass_on_complete_evidence(self):
        p = self._abs("a.py")
        with open(p, "w", encoding="utf-8") as f:
            f.write("x = 1")
        task = make_task(
            allowed_paths=[self.tmp + os.sep],
            definition_of_done=["a.py exists"],
            artifacts=[p],
            evidence=[{"type": "file_created", "path": p, "note": "a.py exists"}],
        )
        r = self.v.verify(self._state(task), task, {})
        self.assertEqual(r["verdict"], "pass")
        self.assertIsNone(r["feedback"])

    def test_pass_on_observation_evidence(self):
        # evidence without a path and empty DoD passes trivially
        task = make_task(allowed_paths=["."], evidence=[{"type": "observation", "note": "done"}])
        r = self.v.verify(self._state(task), task, {})
        self.assertEqual(r["verdict"], "pass")

    def test_fail_no_evidence(self):
        task = make_task()
        r = self.v.verify(self._state(task), task, {})
        self.assertEqual(r["verdict"], "fail")
        self.assertIn("evidence", r["feedback"].lower())

    def test_fail_missing_file(self):
        task = make_task(
            allowed_paths=[self.tmp + os.sep],
            definition_of_done=["a.py exists"],
            artifacts=[self._abs("a.py")],   # never created on disk
            evidence=[{"type": "file_created", "path": self._abs("a.py"), "note": "a.py exists"}],
        )
        r = self.v.verify(self._state(task), task, {})
        self.assertEqual(r["verdict"], "fail")
        self.assertIn("missing", r["feedback"].lower())

    def test_fail_path_outside_allowed(self):
        p = self._abs("secret.py")  # outside allowed_paths -> tmp/../tmp OTHER dir
        outside = self._abs("outside") + os.sep
        os.makedirs(self._abs("outside"), exist_ok=True)
        p2 = self._abs("outside") + os.sep + "x.py"
        with open(p2, "w", encoding="utf-8") as f:
            f.write("x")
        task = make_task(
            allowed_paths=[self.tmp + os.sep + "src" + os.sep],  # allows only src/
            definition_of_done=["x.py exists"],
            artifacts=[p2],
            evidence=[{"type": "file_created", "path": p2, "note": "x.py exists"}],
        )
        r = self.v.verify(self._state(task), task, {})
        self.assertEqual(r["verdict"], "fail")
        self.assertIn("allowed", r["feedback"].lower())

    def test_fail_uncovered_definition_of_done(self):
        task = make_task(
            allowed_paths=["."],
            definition_of_done=["zzz totally unrelated"],
            evidence=[{"type": "observation", "note": "did some work"}],
        )
        r = self.v.verify(self._state(task), task, {})
        self.assertEqual(r["verdict"], "fail")
        self.assertIn("not covered", r["feedback"].lower())

    def test_fail_missing_test_pass_when_dod_mentions_tests(self):
        task = make_task(
            allowed_paths=["."],
            definition_of_done=["all tests pass"],
            evidence=[{"type": "observation", "note": "done"}],  # no test_pass type
        )
        r = self.v.verify(self._state(task), task, {})
        self.assertEqual(r["verdict"], "fail")
        self.assertIn("test", r["feedback"].lower())

    def test_pass_when_test_pass_evidence_provided(self):
        task = make_task(
            allowed_paths=["."],
            definition_of_done=["all tests pass"],
            evidence=[{"type": "test_pass", "note": "12 passed"}],
        )
        r = self.v.verify(self._state(task), task, {})
        self.assertEqual(r["verdict"], "pass")


if __name__ == "__main__":
    unittest.main()
