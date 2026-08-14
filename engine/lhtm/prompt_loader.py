# engine/lhtm/prompt_loader.py
"""Load skill/policy markdown files from the repo into prompt text."""
from pathlib import Path


class PromptLoader:
    def __init__(self, repo_root: str):
        self.repo_root = Path(repo_root)

    def load(self, *names: str) -> str:
        """Concatenate the named files (repo-root-relative) as text.

        Missing files are skipped. Returns "" if nothing loads.
        """
        parts = []
        for name in names:
            p = self.repo_root / name
            try:
                parts.append(p.read_text(encoding="utf-8"))
            except OSError:
                continue  # skip unreadable file, same as missing
        return "\n\n".join(parts)