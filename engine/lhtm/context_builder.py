# engine/lhtm/context_builder.py
"""Thin wrapper over ContextBudget; redacts model-facing output."""
from .context_budget import ContextBudget
from .redactor import Redactor


class ContextBuilder:
    def __init__(self, repo_root: str = "."):
        self.budget = ContextBudget()
        self.redactor = Redactor()

    def build(self, state, task, config, errors=None) -> str:
        text = self.budget.build(state, task, config, errors=errors)
        if config.get("security", {}).get("redact_secrets", True):
            text = self.redactor.redact(text)
        return text
