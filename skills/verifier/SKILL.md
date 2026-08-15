---
name: verifier
description: Verify claimed_done evidence against definition_of_done and emit a verdict.
---

# Verifier Skill - Evidence Verification

Requires: `lhtm-core` (the 10 non-negotiable rules apply).

## When called
When a task is in `claimed_done` status, verify it against its `definition_of_done`.

## Verification process
1. Load the task's `definition_of_done` and `evidence`.
2. For each item in `definition_of_done`, check if evidence covers it.
3. Check: files exist, paths are in `allowed_paths`, test results are present.
4. If all pass -> output `{"task_id": "...", "status": "verified_done", "verdict": "pass"}`
5. If any fail -> output `{"task_id": "...", "status": "failed", "verdict": "needs_more_work", "feedback": "..."}`
