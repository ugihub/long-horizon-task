# scripts/run_supervised.py
"""End-to-end supervised execution demo (P3). ASCII output, no LLM API.

Simulates an LLM by returning canned lhtm-update blocks. The action gate +
safe executor + engine do the real work. Approvals are auto-granted here
via a policy callback so the script is non-interactive.
"""
import sys, os, shutil, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.lhtm.engine import LhtmEngine
from engine.lhtm.config import Config
from engine.lhtm.task_scheduler import TaskScheduler
from engine.lhtm.action_gate import ActionGate
from engine.lhtm.safe_executor import SafeExecutor
from engine.lhtm.context_builder import ContextBuilder
from engine.lhtm.audit import AuditLogger


def simulate_llm(task):
    """Return a canned lhtm-update for the given task (driver = fake LLM)."""
    if task["id"] == "T01":
        return {
            "task_id": "T01",
            "status": "claimed_done",
            "evidence": [{"type": "file_created", "path": "src/cli.py", "note": "created"}],
            "artifacts": ["src/cli.py"],
            "proposed_actions": [
                {"action": "write_file", "path": "src/cli.py",
                 "content": "print('todo app v1')\n"},
                {"action": "run_command", "tool": "python", "args": ["-c", "print('ok')"]},
            ],
            "context": {"rationale": "scaffold done", "next_step": "T02"},
        }
    return {
        "task_id": "T02",
        "status": "claimed_done",
        "evidence": [{"type": "file_created", "path": "src/parser.py", "note": "created"}],
        "artifacts": ["src/parser.py"],
        "proposed_actions": [
            {"action": "write_file", "path": "src/parser.py", "content": "def parse(a): return a\n"},
        ],
        "context": {"rationale": "parser done", "next_step": "none"},
    }


def main():
    base_dir = tempfile.mkdtemp(prefix="lhtm-demo-")
    engine = LhtmEngine(base_dir)
    cfg = Config(base_dir)
    # gate checks config-level allowed_commands (not task.allowed_commands), and the
    # default list lacks python; add it so T01's run_command reaches the executor.
    cfg.data["allowed_commands"] = cfg.data["allowed_commands"] + ["python"]
    scheduler = TaskScheduler()
    gate = ActionGate()
    executor = SafeExecutor(cfg.data)
    builder = ContextBuilder()
    audit = AuditLogger(str(engine.store.events_path))

    goal = "Build a CLI todo app with add/list/done commands"
    engine.set_goal(goal)
    engine.state["mode"] = cfg.data["mode"].upper()

    plan = {
        "schema_version": "1.0",
        "run_id": engine.state["run_id"],
        "goal_hash": engine.state["goal"]["hash"],
        "title": "Todo App",
        "objective": goal,
        "tasks": [
            {"id": "T01", "title": "Scaffold", "objective": "Init cli.py",
             "status": "pending", "depends_on": [], "risk_level": "low",
             "allowed_paths": ["src/"], "allowed_commands": ["python"],
             "definition_of_done": ["cli.py exists"], "artifacts": [],
             "evidence": [], "attempts": 0, "max_attempts": 3},
            {"id": "T02", "title": "Parser", "objective": "Add parser.py",
             "status": "pending", "depends_on": ["T01"], "risk_level": "low",
             "allowed_paths": ["src/"], "allowed_commands": [],
             "definition_of_done": ["parser.py exists"], "artifacts": [],
             "evidence": [], "attempts": 0, "max_attempts": 3},
        ],
        "open_questions": [], "metadata": {}, "approved": False,
    }
    engine.load_plan(plan)
    engine.approve_plan()
    print(f"Goal: {goal}")
    print(f"Plan approved -> phase {engine.state['phase']}, mode {cfg.data['mode']}")

    for step in range(cfg.data["limits"]["max_steps"]):
        active = engine.state.get("active_task_id")
        if active:
            task = next(t for t in engine.state["tasks"] if t["id"] == active)
        else:
            task = scheduler.pick_next(engine.state)
            if task is None:
                print("No next task. Done.")
                break
            if task.get("requires_approval"):
                print(f"High-risk task {task['id']} requires approval (granted).")
            scheduler.promote_to_ready(engine.state, task["id"])
            engine._save()
            engine.activate_task(task["id"])
            task = next(t for t in engine.state["tasks"] if t["id"] == task["id"])

        # mark deps verified for the demo (real verifier comes in P4)
        for t in engine.state["tasks"]:
            if t["status"] == "claimed_done":
                t["status"] = "verified_done"
        engine._save()

        ctx = builder.build(engine.state, task, cfg.data)
        update = simulate_llm(task)
        # gate + execute each proposed action
        for action in update.get("proposed_actions", []):
            decision = gate.check(action, task, cfg.data, engine.state.get("mode"), task["id"])
            if not decision["allowed"]:
                print(f"  [gate] REJECTED {action['action']} {action.get('path', '')}: {decision['reason']}")
                continue
            approval = decision["requires_approval"]  # demo grants all approvals
            result = executor.execute(action, {**decision, "approval_granted": approval}, task)
            audit.log_step(run_id=engine.state["run_id"], phase=engine.state["phase"],
                           active_task_id=task["id"], action=action["action"],
                           result="ok" if result["ok"] else "error", duration_ms=0)
            status = "ok" if result["ok"] else "error"
            print(f"  [exec] {action['action']} {action.get('path', '')}: {status}")

        # engine processes the status update (evidence, artifacts)
        result = engine.process_update(update)
        print(f"[engine] update {update['task_id']} -> {update['status']}: "
              f"{'accepted' if result['accepted'] else result['errors']}")
        if not result["accepted"]:
            break

        if update["status"] == "claimed_done":
            # engine keeps active_task_id set on claimed_done; clear it and mark the
            # task verified here so the scheduler can advance (real verifier in P4).
            engine.state["active_task_id"] = None
            task["status"] = "verified_done"
            engine._save()

    print()
    print("=" * 60)
    print(engine.render_tracker())
    print("=" * 60)
    print("\nAudit events (step):")
    for e in engine.get_events():
        if e.get("event") == "step":
            print(f"  [{e['action']}] {e['result']} ({e['duration_ms']}ms)")
    print("\nV Supervised Tahap 2 demo passed!")
    shutil.rmtree(base_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
