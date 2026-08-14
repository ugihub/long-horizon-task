# engine/lhtm/task_scheduler.py
"""Choose the next task to execute (deterministic)."""


class TaskScheduler:
    def pick_next(self, state: dict) -> dict | None:
        """Return the next runnable task (still 'pending'), or None.

        A task qualifies when:
          - status == 'pending'
          - every task in depends_on has status 'verified_done'
          - attempts < max_attempts
        High-risk tasks are marked requires_approval unless mode is FULL_AUTO.
        """
        mode = state.get("mode", "SUPERVISED")
        task_ids = {t.get("id") for t in state.get("tasks", [])}
        verified = {t["id"] for t in state.get("tasks", [])
                    if t.get("status") == "verified_done"}
        for t in state.get("tasks", []):
            if t.get("status") != "pending":
                continue
            if t.get("attempts", 0) >= t.get("max_attempts", 3):
                continue
            deps = t.get("depends_on", [])
            # unknown dep that is not present at all -> not satisfied
            if any(d not in verified for d in deps):
                continue
            result = dict(t)
            if t.get("risk_level") == "high" and mode != "FULL_AUTO":
                result["requires_approval"] = True
            return result
        return None

    def promote_to_ready(self, state: dict, task_id: str) -> dict | None:
        """Mark a pending task 'ready' (used by the driver before activation)."""
        for t in state.get("tasks", []):
            if t["id"] == task_id and t.get("status") == "pending":
                t["status"] = "ready"
                return t
        return None
