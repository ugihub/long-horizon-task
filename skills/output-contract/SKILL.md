---
name: output-contract
description: The lhtm-update fenced block format, allowed statuses, and proposed_actions schema.
---

# Output Contract - lhtm-update Block

Requires: `lhtm-core` (the 10 non-negotiable rules apply).

## Format
Every response must end with a fenced JSON block:

```lhtm-update
{
  "task_id": "T01",
  "status": "active|claimed_done|failed|blocked",
  "evidence": [{"type": "file_created|test_pass|observation", "path": "...", "note": "..."}],
  "artifacts": ["path/to/file.ext"],
  "context": {"rationale": "...", "next_step": "..."}
}
```

## Statuses you MAY use
- `pending`, `ready`, `active`, `blocked`, `claimed_done`, `failed`

## Statuses you MUST NOT use
- `verified_done` (engine decides)
- `skipped` (engine decides)
- `completed` (phase-level, not per-task)

## Rules
- `claimed_done` REQUIRES at least one evidence entry
- `failed` REQUIRES a rationale explaining why
- Keep `context.next_step` concrete
- The engine parses this block deterministically - follow the format exactly

## Proposed Actions (P3)
You MAY include an optional `proposed_actions` list. Each entry is one action:

```json
{"action": "write_file", "path": "app/api.py", "content": "..."}
{"action": "run_command", "tool": "pytest", "args": ["-q"]}
{"action": "read_file", "path": "src/a.py"}
{"action": "delete_file", "path": "src/old.py"}
{"action": "ask_user", "question": "..."}
```

Rules:
- Paths must be inside the active task's `allowed_paths`. The engine rejects others.
- Sensitive files (`.env`, `*.pem`, `*.key`, `.aws/`, `.kube/`) are always blocked.
- `run_command` must match the configured allowlist (e.g. `pytest`, `ruff`). Raw shell is rejected.
- `write_file`, `delete_file`, `run_command` require user approval in SUPERVISED mode.
- Actions that fail the gate are not executed; you receive the reason.
