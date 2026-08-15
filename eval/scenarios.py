# eval/scenarios.py
"""Load fixtures and run each through the real engine pieces (no LLM)."""
import json
import os
import shutil
import tempfile

from engine.lhtm.engine import LhtmEngine
from engine.lhtm.config import Config
from engine.lhtm.action_gate import ActionGate
from engine.lhtm.safe_executor import SafeExecutor


def load_fixtures(fixtures_dir: str = "eval/fixtures") -> list:
    """Return a sorted list of fixture dicts from all *.json under fixtures_dir."""
    fixtures = []
    for root, _, files in os.walk(fixtures_dir):
        for fn in sorted(files):
            if not fn.endswith(".json"):
                continue
            path = os.path.join(root, fn)
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
            except (ValueError, OSError):
                continue  # broken fixture skipped; not a pass
            if isinstance(data, dict) and data.get("name"):
                fixtures.append(data)
    fixtures.sort(key=lambda d: d["name"])
    return fixtures


def _gate_reason_class(decision: dict) -> str:
    """'secret' if the rejection is sensitive-path, else 'scope'."""
    reason = decision.get("reason", "")
    return "secret" if "sensitive" in reason or "blocked" in reason else "scope"


def _run_engine(base_dir: str, fixture: dict) -> dict:
    """Build the engine in base_dir and drive the fixture updates. Returns record."""
    engine = LhtmEngine(base_dir)
    cfg = Config(base_dir)
    cfg.data["allowed_commands"] = cfg.data["allowed_commands"] + ["python"]
    gate = ActionGate()
    executor = SafeExecutor(cfg.data)

    engine.set_goal(fixture["goal"])
    engine.state["mode"] = cfg.data["mode"].upper()

    plan = dict(fixture["plan"])
    plan["schema_version"] = "1.0"
    plan["goal_hash"] = engine.state["goal"]["hash"]
    plan["open_questions"] = []
    plan["metadata"] = {}
    plan["approved"] = False
    engine.load_plan(plan)
    engine.approve_plan()

    schema_ok = True
    out_of_scope = 0
    secret_leak = 0
    # count of gate-rejected actions that were nevertheless executed; the loop
    # skips rejected actions, so it is 0 today and only rises if someone
    # changes the loop to execute rejected actions.
    escaped = 0

    for update in fixture["updates"]:
        task = engine._find_task(update["task_id"])
        # activate the task if it is ready (scheduler-style promote)
        if task is not None and task.get("status") == "pending":
            task["status"] = "ready"
            engine._save()
        if task is not None and task.get("status") == "ready":
            engine.activate_task(update["task_id"])

        for action in update.get("proposed_actions", []):
            active = engine.state.get("active_task_id")
            t = engine._find_task(active) if active else None
            if t is None:
                continue
            decision = gate.check(action, t, cfg.data, engine.state.get("mode"), t["id"])
            if not decision["allowed"]:
                cls = _gate_reason_class(decision)
                if cls == "secret":
                    secret_leak += 1
                else:
                    out_of_scope += 1
                continue
            # grant the approval when one is required (mirrors run_supervised.py)
            decision["approval_granted"] = decision["requires_approval"]
            executor.execute(action, decision, t)

        result = engine.process_update(update)
        if not result.get("accepted"):
            schema_ok = False
        rec = update.get("recovery")
        if rec:
            engine.recover(update["task_id"], rec)

    last = fixture["plan"]["tasks"][-1]["id"]
    final_task = engine._find_task(last)
    final_status = final_task.get("status") if final_task else "?"

    expected = fixture.get("expected", {})
    test_pass = (expected.get("test_pass", True)
                 == (final_status == "verified_done"))
    completed = all(
        engine._find_task(t["id"]).get("status") in ("verified_done", "failed", "skipped")
        for t in fixture["plan"]["tasks"]
    )
    return {
        "name": fixture["name"],
        "category": fixture["category"],
        "schema_ok": schema_ok,
        "final_status": final_status,
        "out_of_scope": out_of_scope,
        "secret_leak": secret_leak,
        "escaped": escaped,
        "test_pass": test_pass,
        "completed": completed,
    }


def run_scenario(fixture: dict, workdir: str | None = None) -> dict:
    """Run one fixture through the engine. Returns a per-run record dict.

    The engine executor + verifier resolve file paths relative to the current
    working directory, so this runs inside an isolated cwd (a temp dir, or the
    caller-provided workdir). The previous cwd is restored before returning.
    """
    prev = os.getcwd()
    base_dir = os.path.abspath(workdir) if workdir else tempfile.mkdtemp(prefix="lhtm-eval-")
    os.makedirs(base_dir, exist_ok=True)
    own_dir = workdir is None
    try:
        os.chdir(base_dir)
        return _run_engine(base_dir, fixture)
    finally:
        os.chdir(prev)
        if own_dir:
            shutil.rmtree(base_dir, ignore_errors=True)
