# Planner Skill — LHTM Plan Generation

Output a JSON plan conforming to schema `lhtm.plan/v1`.

## Output Format

```json
{
  "schema_version": "1.0",
  "run_id": "<from state>",
  "goal_hash": "<sha256 hash of goal>",
  "title": "<plan title>",
  "objective": "<one-sentence goal>",
  "tasks": [
    {
      "id": "T01",
      "title": "<short name>",
      "objective": "<what this task achieves>",
      "status": "pending",
      "depends_on": [],
      "risk_level": "low|medium|high",
      "allowed_paths": ["<relative paths>"],
      "allowed_commands": [],
      "definition_of_done": ["<specific, verifiable items>"],
      "artifacts": [],
      "evidence": [],
      "attempts": 0,
      "max_attempts": 3
    }
  ],
  "open_questions": ["<questions for user before approval>"],
  "metadata": {
    "model": "<model name>",
    "generated_at": "<ISO8601>",
    "generator": "planner"
  },
  "approved": false
}
```

## Rules
- Task IDs: T01, T02, ...
- `depends_on` must reference existing task IDs
- No cyclic dependencies
- All tasks start `pending`
- `definition_of_done` must be specific and verifiable
- Include `open_questions` for anything uncertain
- Risk level: low = read-only, medium = file edit, high = destructive command
