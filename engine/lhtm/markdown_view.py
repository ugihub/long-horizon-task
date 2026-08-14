# engine/lhtm/markdown_view.py
from datetime import datetime, timezone

class MarkdownView:
    def render_tracker(self, state: dict) -> str:
        lines = []
        lines.append("# LHTM Progress Tracker")
        lines.append(f"")
        lines.append(f"- **Goal:** {state.get('goal', {}).get('text', 'N/A')}")
        lines.append(f"- **Phase:** {state.get('phase', 'N/A')}")
        lines.append(f"- **Mode:** {state.get('mode', 'N/A')}")
        lines.append(f"- **Active Task:** {state.get('active_task_id', '—')}")
        lines.append(f"- **Run ID:** {state.get('run_id', 'N/A')}")
        lines.append(f"- **Generated:** {datetime.now(timezone.utc).isoformat()}")
        lines.append(f"")

        tasks = state.get("tasks", [])
        if not tasks:
            lines.append("_No tasks defined._")
        else:
            lines.append("| ID | Title | Status | Deps | Risk | Attempts | Evidence |")
            lines.append("|----|-------|--------|------|------|----------|----------|")
            for t in tasks:
                tid = t["id"]
                marker = "▶ " if tid == state.get("active_task_id") else "  "
                title = t.get("title", "?")
                status = t.get("status", "?")
                deps = ",".join(t.get("depends_on", [])) or "—"
                risk = t.get("risk_level", "?")
                attempts = f"{t.get('attempts', 0)}/{t.get('max_attempts', 3)}"
                ev = "✓" if t.get("evidence") else "—"
                lines.append(f"| {marker}{tid} | {title} | {status} | {deps} | {risk} | {attempts} | {ev} |")

        lines.append(f"")
        lines.append(f"---")
        lines.append(f"*LHTM v{state.get('schema_version', '?')} — auto-generated from canonical state*")
        return "\n".join(lines)
