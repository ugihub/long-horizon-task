# eval/harness.py
"""Orchestrate fixture runs + metric evaluation."""
from .metrics import evaluate
from .scenarios import load_fixtures, run_scenario


class EvalHarness:
    def __init__(self, fixtures_dir: str = "eval/fixtures"):
        self.fixtures_dir = fixtures_dir

    def run(self, fixtures: list | None = None) -> dict:
        fx = fixtures if fixtures is not None else load_fixtures(self.fixtures_dir)
        results = [run_scenario(f) for f in fx]
        summary = evaluate(results)
        return {"results": results, "metrics": summary["metrics"],
                "passed": summary["passed"]}