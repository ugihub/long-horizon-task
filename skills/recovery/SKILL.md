---
name: recovery
description: Choose a recovery action when a task fails or the system enters RECOVERY phase.
---

# Recovery Skill - Error Recovery Actions

Requires: `lhtm-core` (the 10 non-negotiable rules apply).

When a task fails or the system enters `RECOVERY` phase, choose one:

| Action | When | How |
|--------|------|-----|
| `retry_with_hint` | Output error, next attempt available | Set status `active`, include hint |
| `decompose_task` | Task too large, keeps failing | Split into sub-tasks, update plan |
| `request_user_input` | Need human decision | Set phase `WAITING_USER`, ask question |
| `mark_blocked` | External dependency missing | Set status `blocked`, record reason |
| `rollback_proposal` | Changes need undoing | Propose restore from snapshot |
| `switch_to_safe_mode` | Repeated failures, risk | Switch mode to `DRY_RUN` or `SUPERVISED` |

## Rules
- Max retries before escalation: `max_attempts` (default 3)
- After 2 consecutive failures, suggest `decompose_task` or `request_user_input`
- Never silently retry the same failing action
