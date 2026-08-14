# engine/lhtm/goal_hash.py
import hashlib
from datetime import datetime, timezone

class GoalHash:
    @staticmethod
    def freeze(text: str) -> dict:
        h = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return {
            "text": text,
            "hash": h,
            "frozen_at": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def check(state: dict) -> None:
        if "hash" not in state or "text" not in state:
            raise ValueError("Goal hash missing from state")
        expected = hashlib.sha256(state["text"].encode("utf-8")).hexdigest()
        if state["hash"] != expected:
            raise ValueError(
                f"Goal mismatch: hash changed. Expected {expected}, got {state['hash']}"
            )
