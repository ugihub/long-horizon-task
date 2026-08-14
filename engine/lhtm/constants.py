# engine/lhtm/constants.py
"""Canonical constants: phase, task status, execution mode, field names."""

SCHEMA_VERSION = "1.0"

# 12 phases (ordered)
PHASES = [
    "DRAFT", "PLANNING", "REVIEW", "APPROVED",
    "READY", "EXECUTING", "VERIFYING", "RECOVERY",
    "WAITING_USER", "COMPLETED", "ABORTED",
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

# Statuses LLM may propose
LLM_WRITABLE_STATUSES = {"pending", "ready", "active", "blocked", "claimed_done", "failed"}
ENGINE_OWNED_STATUSES = {"verified_done", "skipped"}

# 4 execution modes
EXECUTION_MODES = ["DRY_RUN", "SUPERVISED", "AUTO_SAFE", "FULL_AUTO"]

# Default policy
DEFAULT_POLICY = {
    "security_level": "default",
    "max_attempts": 3,
    "max_repair_attempts": 2,
}

# Phase transition: legal = forward (index >= current) or to RECOVERY/WAITING_USER/ABORTED
def is_legal_phase_transition(current: str, target: str) -> bool:
    if target not in PHASE_INDEX or current not in PHASE_INDEX:
        return False
    if target in ("RECOVERY", "WAITING_USER", "ABORTED"):
        return True
    return PHASE_INDEX[target] >= PHASE_INDEX[current]
