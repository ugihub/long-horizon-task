# tests/test_release_ascii.py
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# dirs that must be fully ASCII (they ship to skill clients or are engine-facing)
REQUIRED_ASCII_DIRS = ["skills", "policies", "examples", "engine", "eval", "scripts", "example"]
# dirs/file exempt from the full-ASCII gate (historical editorial + diagrams)
SKIP = (".git", ".lhtm", ".pytest_cache", "__pycache__", "eval/report.md")


def _rel(p):
    return os.path.relpath(p, ROOT).replace(os.sep, "/")


class TestReleaseAscii(unittest.TestCase):
    def test_required_dirs_are_ascii(self):
        bad = []
        for d in REQUIRED_ASCII_DIRS:
            base = os.path.join(ROOT, d)
            if not os.path.isdir(base):
                continue  # dir not created yet (e.g. example/ before Task 7)
            for root, _, files in os.walk(base):
                for f in files:
                    p = os.path.join(root, f)
                    try:
                        txt = open(p, encoding="utf-8").read()
                    except (OSError, UnicodeDecodeError):
                        continue
                    hits = [(i + 1, ch) for i, ch in enumerate(txt) if ord(ch) > 127]
                    if hits:
                        bad.append((_rel(p), hits[:3]))
        self.assertEqual(bad, [], f"non-ASCII in required dirs: {bad[:5]}")

    def test_no_arrows_or_corruption_anywhere(self):
        bad = []
        for root, dirs, files in os.walk(ROOT):
            dirs[:] = [d for d in dirs if d not in SKIP]
            for f in files:
                p = os.path.join(root, f)
                rel = _rel(p)
                if rel == "eval/report.md":
                    continue
                try:
                    txt = open(p, encoding="utf-8").read()
                except (OSError, UnicodeDecodeError):
                    continue
                for i, ch in enumerate(txt):
                    if ord(ch) in (0x2192, 0xFFFD):
                        bad.append((rel, i + 1, "U+%04X" % ord(ch)))
                        break
        self.assertEqual(bad, [], f"arrows or corruption: {bad[:5]}")


if __name__ == "__main__":
    unittest.main()
