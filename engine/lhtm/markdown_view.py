# engine/lhtm/markdown_view.py
from datetime import datetime, timezone


def _md_cell(value) -> str:
    """Escape a value for a markdown table cell."""
    if not isinstance(value, (str, int, float)):
        value = str(value) if value is not None else ""
    text = str(value)
    return text.replace("|", "\\|").replace("\n", " ").replace("\r", " ")


class MarkdownView:
    def render_tracker(self, state: dict) -> str:
        lines = []
        lines.append("# LHTM Progress Tracker")
        lines.append("")
        lines.append(f"- **Goal:** {_md_cell(state.get('goal', {}).get('text', 'N/A'))}")
        lines.append(f"- **Phase:** {_md_cell(state.get('phase', 'N/A'))}")
        lines.append(f"- **Mode:** {_md_cell(state.get('mode', 'N/A'))}")
        lines.append(f"- **Active Task:** {_md_cell(state.get('active_task_id', '—'))}")
        lines.append(f"- **Run ID:** {_md_cell(state.get('run_id', 'N/A'))}")
        lines.append(f"- **Generated:** {datetime.now(timezone.utc).isoformat()}")
        lines.append("")

        tasks = state.get("tasks", [])
        if not tasks:
            lines.append("_No tasks defined._")
        else:
            lines.append("| ID | Title | Status | Deps | Risk | Attempts | Evidence |")
            lines.append("|----|-------|--------|------|------|----------|----------|")
            for t in tasks:
                if not isinstance(t, dict):
                    continue
                tid = t.get("id", "?")
                marker = "▶ " if tid == state.get("active_task_id") else "  "
                title = _md_cell(t.get("title", "?"))
                status = _md_cell(t.get("status", "?"))
                deps = _md_cell(",".join(t.get("depends_on", [])) or "—")
                risk = _md_cell(t.get("risk_level", "?"))
                attempts = f"{t.get('attempts', 0)}/{t.get('max_attempts', 3)}"
                ev = "✓" if t.get("evidence") else "—"
                lines.append(f"| {marker}{_md_cell(tid)} | {title} | {status} | {deps} | {risk} | {attempts} | {ev} |")

        lines.append("")
        lines.append("---")
        lines.append(f"*LHTM v{_md_cell(state.get('schema_version', '?'))} — auto-generated from canonical state*")
        return "\n".join(lines)
