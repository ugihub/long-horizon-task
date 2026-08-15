# eval/main.py
"""P8 entry point: run all fixtures, write eval/report.md, exit 0/1."""
import os
import sys

from .harness import EvalHarness
from .report import render_report


def run() -> int:
    root = os.path.dirname(os.path.abspath(__file__))
    harness = EvalHarness(os.path.join(root, "fixtures"))
    out = harness.run()
    md = render_report(out["results"], out["metrics"], out["passed"])
    report_path = os.path.join(root, "report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"P8 eval: {len(out['results'])} cases, passed={out['passed']}")
    print(f"Report written to {report_path}")
    return 0 if out["passed"] else 1


if __name__ == "__main__":
    sys.exit(run())