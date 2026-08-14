# engine/lhtm/schema_validator.py
from .constants import (
    SCHEMA_VERSION, PHASES, TASK_STATUSES,
    LEGAL_TASK_TRANSITIONS,
    ENGINE_OWNED_STATUSES, EXECUTION_MODES, is_legal_phase_transition,
)

REQUIRED_TASK_FIELDS = [
    "id", "title", "objective", "status", "depends_on",
    "risk_level", "allowed_paths", "allowed_commands",
    "definition_of_done", "artifacts", "evidence", "attempts", "max_attempts",
]


def _validate_task(t: dict, initial_only: bool = False) -> list[str]:
    """Validate a single task dict. Returns list of error strings."""
    errs = []
    tid = t.get("id", "?")
    for field in REQUIRED_TASK_FIELDS:
        if field not in t:
            errs.append(f"task {tid}: missing field '{field}'")
    if t.get("status") not in TASK_STATUSES:
        errs.append(f"task {tid}: invalid status '{t.get('status')}'")
    if initial_only and t.get("status") != "pending":
        errs.append(f"task {tid}: initial status must be 'pending', got '{t.get('status')}'")
    return errs


class SchemaValidator:
    def validate_state(self, state: dict) -> list[str]:
        errs = []
        if state.get("schema_version") != SCHEMA_VERSION:
            errs.append(f"schema_version must be '{SCHEMA_VERSION}', got '{state.get('schema_version')}'")
        if state.get("phase") not in PHASES:
            errs.append(f"invalid phase: '{state.get('phase')}'. Must be one of {PHASES}")
        if state.get("mode") not in EXECUTION_MODES:
            errs.append(f"invalid mode: '{state.get('mode')}'. Must be one of {EXECUTION_MODES}")
        if "goal" not in state or "hash" not in state.get("goal", {}):
            errs.append("state missing goal.hash")
        for t in state.get("tasks", []):
            errs.extend(_validate_task(t))
        return errs

    def validate_plan(self, plan: dict) -> list[str]:
        errs = []
        if plan.get("schema_version") != SCHEMA_VERSION:
            errs.append("plan schema_version mismatch")
        task_ids = set()
        for t in plan.get("tasks", []):
            tid = t.get("id", "?")
            if tid in task_ids:
                errs.append(f"duplicate task id: '{tid}'")
            task_ids.add(tid)
            errs.extend(_validate_task(t, initial_only=True))
        # check depends_on references exist
        for t in plan.get("tasks", []):
            for dep in t.get("depends_on", []):
                if dep not in task_ids:
                    errs.append(f"task {t.get('id', '?')}: depends_on '{dep}' not found in task list")
        # cycle detection (topological sort)
        edges = []
        for t in plan.get("tasks", []):
            for dep in t.get("depends_on", []):
                edges.append((dep, t.get("id", "?")))
        if self._has_cycle(task_ids, edges):
            errs.append("cyclic dependency detected in plan tasks")
        # goal_hash present
        if not plan.get("goal_hash"):
            errs.append("plan missing goal_hash")
        return errs

    def _has_cycle(self, nodes: set, edges: list) -> bool:
        # DFS-based cycle detection
        adj = {n: [] for n in nodes}
        for u, v in edges:
            if u in adj:
                adj[u].append(v)
        visited = set()
        rec_stack = set()
        def dfs(n):
            visited.add(n)
            rec_stack.add(n)
            for nb in adj.get(n, []):
                if nb not in visited:
                    if dfs(nb):
                        return True
                elif nb in rec_stack:
                    return True
            rec_stack.discard(n)
            return False
        for n in nodes:
            if n not in visited:
                if dfs(n):
                    return True
        return False

    def validate_update(self, update: dict) -> list[str]:
        errs = []
        status = update.get("status")
        if status not in TASK_STATUSES:
            errs.append(f"invalid status: '{status}'")
        elif status in ENGINE_OWNED_STATUSES:
            errs.append(f"status '{status}' is engine-owned. LLM may not set it.")
        elif status == "active":
            errs.append("status 'active' is engine-owned via activate_task. LLM may not set it.")
        if status == "claimed_done" and not update.get("evidence"):
            errs.append("claimed_done requires evidence")
        return errs

    def validate_transition(self, from_status: str, to_status: str) -> list[str]:
        allowed = LEGAL_TASK_TRANSITIONS.get(from_status, set())
        if to_status not in allowed:
            return [f"illegal transition: '{from_status}' -> '{to_status}'. Allowed: {allowed}"]
        return []

    def validate_phase_transition(self, current: str, target: str) -> list[str]:
        if is_legal_phase_transition(current, target):
            return []
        return [f"illegal phase transition: '{current}' -> '{target}'"]
