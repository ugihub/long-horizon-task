# Executor Skill - Per-Turn Execution

## Input
- Active task card (from planner)
- Current state (phase, mode, active_task_id)
- Previous errors/hints (if any)

## Per-turn protocol
1. Read the active task's `objective`, `definition_of_done`, `allowed_paths`, `allowed_commands`.
2. Determine the next step to move toward completion.
3. Propose your action as an `lhtm-update` block.
4. Include evidence if claiming done.

## Constraints
- Only one task: `active_task_id`. Do not work on other tasks.
- Only paths in `allowed_paths`. Do not touch files outside.
- `claimed_done` requires evidence for every item in `definition_of_done`.
- Max attempts per task is `max_attempts`. After that, propose `failed`.
- Propose actions via `proposed_actions`; the engine's action gate validates each one.
- `write_file`/`delete_file`/`run_command` need user approval in SUPERVISED mode.
- If an action is rejected, read the reason and propose a corrected action.
