# scripts/ascii_sweep.py
"""Repo-wide ASCII hygiene sweep (P9). Converts common non-ASCII glyphs to ASCII.

Preserves box-drawing block chars (U+2500-257F) and smart quotes (U+2018-201F),
which appear in historical design diagrams and quoted samples where conversion
would mangle content. Run once, review the diff, then the test suite locks it.
"""
import os

_REPLACEMENTS_CHARS = {
    0x00a7: 'sec.',
    0x2013: '-',
    0x2014: '--',
    0x2192: '->',
    0x25b6: '>',
    0x25bc: 'v',
    0x2705: '[x]',
    0x2713: '[x]',
}
REPLACEMENTS = {chr(k): v for k, v in _REPLACEMENTS_CHARS.items()}

SKIP_DIRS = {".git", ".lhtm", ".pytest_cache", "__pycache__"}
SKIP_FILES = {"eval/report.md"}


def _skipped(rel: str) -> bool:
    return rel == "eval/report.md"


def sweep(root: str = ".") -> list:
    changed = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            p = os.path.join(dirpath, fn)
            rel = os.path.relpath(p, root).replace(os.sep, "/")
            if _skipped(rel):
                continue
            try:
                with open(p, encoding="utf-8") as f:
                    txt = f.read()
            except (OSError, UnicodeDecodeError):
                continue
            out = []
            for ch in txt:
                code = ord(ch)
                if 0x2500 <= code <= 0x257F or 0x2018 <= code <= 0x201F:
                    out.append(ch)
                else:
                    out.append(REPLACEMENTS.get(ch, ch))
            new = "".join(out)
            if new != txt:
                with open(p, "w", encoding="utf-8", newline="") as f:
                    f.write(new)
                changed.append(rel)
    return changed


if __name__ == "__main__":
    changed = sweep()
    print(f"ASCII sweep: {len(changed)} files changed")
    for c in sorted(changed):
        print("  ", c)
