# engine/lhtm/project_facts.py
"""Read-only repo scan: size-capped file summary, respects allowed/blocked paths."""
import os
from pathlib import Path

from .action_gate import _is_sensitive

TOP_N = 5


class ProjectFacts:
    def __init__(self, repo_root: str = ".", config=None):
        self.root = Path(repo_root)
        self.config = config or {}

    def scan(self, allowed_paths) -> dict:
        blocked = self.config.get("blocked_paths", [])
        max_chars = int(self.config.get("limits", {}).get("max_facts_chars", 1500))
        root_resolved = self.root.resolve()
        files = []
        for ap in allowed_paths:
            base = (self.root / ap.rstrip("/\\")).resolve()
            if not base.is_relative_to(root_resolved):
                continue  # skip paths outside the repo root
            if not base.exists():
                continue
            if base.is_file():
                cands = [base]
            else:
                cands = [p for p in base.rglob("*") if p.is_file()]
            for p in cands:
                rel = os.path.relpath(str(p), str(self.root)).replace("\\", "/")
                if _is_sensitive(rel, blocked):
                    continue
                try:
                    lines = len(p.read_text(encoding="utf-8", errors="replace").splitlines())
                except OSError:
                    lines = 0
                files.append({"path": rel, "lines": lines})
        files.sort(key=lambda f: (-f["lines"], f["path"]))
        top = files[:TOP_N]
        summary = "\n".join(f"{f['path']} ({f['lines']} lines)" for f in top)
        if len(summary) > max_chars:
            summary = summary[:max_chars] + "\n... (truncated)"
        return {"files": top, "summary": summary}

    def excerpts(self, allowed_paths, n: int = 3, max_chars: int | None = None) -> list[str]:
        mc = max_chars or int(self.config.get("limits", {}).get("max_excerpt_chars", 2000))
        facts = self.scan(allowed_paths)
        out = []
        for f in facts["files"][:n]:
            p = self.root / f["path"]
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            out.append(f"### {f['path']}\n{text[:mc]}")
        return out

    def render(self, allowed_paths) -> str:
        facts = self.scan(allowed_paths)
        return "# LHTM Project Facts\n" + facts["summary"]
