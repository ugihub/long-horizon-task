# tests/test_eval_main.py
import os
import sys
import unittest


class TestEvalMain(unittest.TestCase):
    def test_eval_is_importable_package(self):
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        import eval  # noqa: F401
        self.assertTrue(hasattr(eval, "__file__"))
