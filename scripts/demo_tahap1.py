# scripts/demo_tahap1.py
"""End-to-end Tahap 1 flow demonstration."""
import sys, json, tempfile
sys.path.insert(0, ".")

from engine.lhtm.engine import LhtmEngine

def main():
    base_dir = ".lhtm"
    engine = LhtmEngine(base_dir)

    # 1. Set goal
    goal = "Build a CLI todo app with add/list/done commands, persistent storage"
    engine.set_goal(goal)
    print(f"Goal frozen: {engine.state['goal']['hash'][:12]}...")

    # 2. Load plan
    plan = {
        "schema_version": "1.0",
        "run_id": engine.state["run_id"],
        "goal_hash": engine.state["goal"]["hash"],
        "title": "Todo App",
        "objective": goal,
        "tasks": [
            {
                "id": "T01", "title": "Project scaffold", "objective": "Init structure",
                "status": "pending", "depends_on": [], "risk_level": "low",
                "allowed_paths": ["src/", "tests/", "cli.py"],
                "allowed_commands": ["mkdir", "touch"],
                "definition_of_done": ["cli.py exists", "src/ dir exists", "tests/ dir exists"],
                "artifacts": [], "evidence": [], "attempts": 0, "max_attempts": 3,
            },
            {
                "id": "T02", "title": "CLI parsing", "objective": "Parse add/list/done",
                "status": "pending", "depends_on": ["T01"], "risk_level": "low",
                "allowed_paths": ["cli.py"],
                "allowed_commands": [],
                "definition_of_done": ["cli.py accepts add", "cli.py accepts list", "cli.py accepts done"],
                "artifacts": [], "evidence": [], "attempts": 0, "max_attempts": 3,
            },
        ],
        "open_questions": ["Use argparse?"],
        "metadata": {"model": "test", "generated_at": "2026-08-14T00:00:00Z", "generator": "planner"},
        "approved": False,
    }
    engine.load_plan(plan)
    print(f"Plan loaded: {len(plan['tasks'])} tasks")

    # 3. Approve plan
    engine.approve_plan()
    print("Plan approved -> phase:", engine.state["phase"])

    # 4. Transition T01: pending -> ready -> active
    engine.state["tasks"][0]["status"] = "ready"
    engine._save()
    engine.activate_task("T01")
    print(f"T01 activated: {engine.state['active_task_id']}")

    # 5. Process update: T01 claimed_done with evidence
    result = engine.process_update({
        "task_id": "T01",
        "status": "claimed_done",
        "evidence": [
            {"type": "file_created", "path": "cli.py", "note": "Created"},
            {"type": "file_created", "path": "src/__init__.py", "note": "Created"},
        ],
        "artifacts": ["cli.py", "src/"],
        "context": {"rationale": "Scaffold done", "next_step": "T02"},
    })
    print(f"Update accepted: {result['accepted']}")
    assert result["accepted"], "Update should be accepted"

    # 6. Show tracker
    print("\n" + "="*60)
    print(engine.render_tracker())
    print("="*60)

    # 7. Show events
    print("\nEvents:")
    for e in engine.get_events():
        print(f"  [{e['event']}] at {e['ts'][:19]}")

    print("\n✓ Tahap 1 E2E passed!")

if __name__ == "__main__":
    main()
