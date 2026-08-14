# engine/lhtm/constants.py
"""Canonical constants: phases, task statuses, execution modes, policy."""

SCHEMA_VERSION = "1.0"

# 12 phases (ordered, per Implementation_plan.md §4.4)
PHASES = [
    "DRAFT", "PLANNING", "PLAN_REVIEW", "READY",
    "EXECUTING", "VERIFYING", "BLOCKED", "WAITING_USER",
    "FAILED", "RECOVERY", "COMPLETED", "ABORTED",
]
PHASE_INDEX = {p: i for i, p in enumerate(PHASES)}

# 8 task statuses
TASK_STATUSES = [
    "pending", "ready", "active", "blocked",
    "claimed_done", "verified_done", "failed", "skipped",
]

# Legal transitions: from -> set(to)
LEGAL_TASK_TRANSITIONS = {
    "pending":     {"ready", "skipped"},
    "ready":       {"active", "blocked", "skipped"},
    "active":      {"claimed_done", "failed", "blocked"},
    "blocked":     {"pending", "ready", "failed"},
    "claimed_done": {"verified_done", "failed", "active"},
    "verified_done": set(),  # terminal
    "failed":      {"ready"},  # only via manual reset with approval
    "skipped":     set(),      # terminal
}

# Statuses LLM may propose via lhtm-update. 'active' is NOT here: the engine
# owns activation (activate_task). ENGINE_OWNED_STATUSES are unreachable by LLM.
LLM_WRITABLE_STATUSES = {"pending", "ready", "blocked", "claimed_done", "failed"}
ENGINE_OWNED_STATUSES = {"active", "verified_done", "skipped"}

# 4 execution modes
EXECUTION_MODES = ["DRY_RUN", "SUPERVISED", "AUTO_SAFE", "FULL_AUTO"]

# Default policy
DEFAULT_POLICY = {
    "security_level": "default",
    "max_attempts": 3,
    "max_repair_attempts": 2,
}

# Phase transition: explicit legal edges per Implementation_plan.md §4.4.
# Legal source->target edges. Any source may also move to RECOVERY_* phases.
# Phases not listed as a source default to "next phase only" (strict forward).
PHASE_TRANSITIONS = {
    "DRAFT":        {"PLANNING", "PLAN_REVIEW"},
    "PLANNING":     {"PLAN_REVIEW", "READY", "DRAFT"},
    "PLAN_REVIEW":  {"READY", "PLANNING"},
    "READY":        {"EXECUTING", "COMPLETED", "PLAN_REVIEW"},
    "EXECUTING":    {"VERIFYING", "BLOCKED"},
    "VERIFYING":    {"READY", "FAILED", "EXECUTING"},
    "FAILED":       {"RECOVERY"},
    "RECOVERY":     {"READY", "EXECUTING"},
    "BLOCKED":      {"WAITING_USER", "EXECUTING"},
    "WAITING_USER": {"READY", "PLANNING"},
    "COMPLETED":    set(),
    "ABORTED":      set(),
}
# Recovery-phase sinks always reachable from any non-terminal phase.
RECOVERY_PHASES = {"BLOCKED", "WAITING_USER", "FAILED", "RECOVERY", "ABORTED"}
TERMINAL_PHASES = {"COMPLETED", "ABORTED"}


def is_legal_phase_transition(current: str, target: str) -> bool:
    if target not in PHASE_INDEX or current not in PHASE_INDEX:
        return False
    # terminal phases cannot exit for any reason
    if current in TERMINAL_PHASES:
        return False
    if target in RECOVERY_PHASES:
        return True
    edges = PHASE_TRANSITIONS.get(current, set())
    if edges:
        return target in edges
    # no explicit row: allow moving to the immediate next phase
    return PHASE_INDEX[target] == PHASE_INDEX[current] + 1
