# Output Contract — lhtm-update Block

## Format
Every response must end with a fenced JSON block:

````
```lhtm-update
{
  "task_id": "T01",
  "status": "active|claimed_done|failed|blocked",
  "evidence": [{"type": "file_created|test_pass|observation", "path": "...", "note": "..."}],
  "artifacts": ["path/to/file.ext"],
  "context": {"rationale": "...", "next_step": "..."}
}
```
````

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
- The engine parses this block deterministically — follow the format exactly
