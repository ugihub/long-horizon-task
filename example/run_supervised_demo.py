# example/run_supervised_demo.py
"""LHTM v2 example project: end-to-end supervised demo (P3+P4), ASCII output.

A copy of scripts/run_supervised.py for the example/ project. Run it from the
repo root or from example/ - it writes temp work + src/ relative to the CWD and
cleans both up. Simulates an LLM with canned lhtm-update blocks; the action gate
+ safe executor + engine verifier do the real work. No LLM API.
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
            "evidence": [{"type": "file_created", "path": "src/cli.py", "note": "cli.py exists"}],
            "artifacts": ["src/cli.py"],
            "proposed_actions": [
                {"action": "write_file", "path": "src/cli.py",
                 "content": "print('todo app v1')\n"},
                {"action": "run_command", "tool": "python", "args": ["-c", "print('ok')"]},
            ],
            "context": {"rationale": "scaffold done", "next_step": "T02"},
        }
    if task["id"] == "T02":
        return {
            "task_id": "T02",
            "status": "claimed_done",
            "evidence": [{"type": "file_created", "path": "src/parser.py", "note": "parser.py exists"}],
            "artifacts": ["src/parser.py"],
            "proposed_actions": [
                {"action": "write_file", "path": "src/parser.py", "content": "def parse(a): return a\n"},
            ],
            "context": {"rationale": "parser done", "next_step": "T03"},
        }
    # T03: claims a file that was never created -> verifier fails
    return {
        "task_id": "T03",
        "status": "claimed_done",
        "evidence": [{"type": "file_created", "path": "src/config.py", "note": "config.py exists"}],
        "artifacts": ["src/config.py"],
        "proposed_actions": [],
        "context": {"rationale": "config done", "next_step": "none"},
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
            {"id": "T03", "title": "Config", "objective": "Add config.py",
             "status": "pending", "depends_on": ["T02"], "risk_level": "low",
             "allowed_paths": ["src/"], "allowed_commands": [],
             "definition_of_done": ["config.py exists"], "artifacts": [],
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

        # engine processes the status update; claimed_done is verified atomically
        result = engine.process_update(update)
        extra = ""
        if result.get("verdict"):
            extra = f" | verdict={result['verdict']}"
        if result.get("feedback"):
            extra += f" | feedback={result['feedback']}"
        print(f"[engine] update {update['task_id']} -> {engine._find_task(update['task_id'])['status']}: "
              f"{'accepted' if result['accepted'] else result['errors']}{extra}")
        if not result["accepted"]:
            break

    # --- Tahap 4: recovery demo ---
    # T03 failed verification (file never created). Drive it through recovery.
    r = engine.recover("T03", {"action": "retry_with_hint", "hint": "create src/config.py then re-claim"})
    print(f"[recovery] retry_with_hint T03 -> {'ok' if r['ok'] else r['error']} "
          f"status={engine._find_task('T03')['status']}")
    r = engine.recover("T03", {"action": "mark_blocked"})
    print(f"[recovery] mark_blocked T03 -> {'ok' if r['ok'] else r['error']} "
          f"status={engine._find_task('T03')['status']}")

    # --- Tahap 4: facts demo ---
    engine.refresh_facts(repo_root=".", allowed_paths=["src/"], config=cfg.data)
    facts_path = os.path.join(base_dir, "project_facts.md")
    print(f"[facts] generated {facts_path}")

    print()
    print("=" * 60)
    from engine.lhtm.redactor import Redactor
    engine.view.redactor = Redactor.from_config(cfg.data)
    print(engine.render_tracker())
    print("=" * 60)
    print("\nAudit events (step):")
    for e in engine.get_events():
        if e.get("event") == "step":
            print(f"  [{e['action']}] {e['result']} ({e['duration_ms']}ms)")
    print("\nV Supervised Tahap 2+3+4 demo passed!")
    shutil.rmtree(base_dir, ignore_errors=True)
    # demo writes are CWD-relative (src/cli.py etc.); clean them up
    shutil.rmtree("src", ignore_errors=True)


if __name__ == "__main__":
    main()
