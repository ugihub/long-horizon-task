---
name: lhtm-core
description: LHTM 10 non-negotiable guardrail rules. Load before planning or executing any LHTM task.
---

# LHTM Core Rules - Non-Negotiable

You are operating under the LHTM (Long Horizon Task Management) system. These rules are deterministic guardrails, not suggestions.

## Using this skill

This is the base skill. Every other LHTM skill (`planner`, `executor`, `verifier`, `recovery`, `output-contract`) builds on these rules. Load this skill first.

## 10 Rules

1. **JSON canonical.** `state.json` is the source of truth. Markdown is a generated view. Never update markdown directly.
2. **One active task.** Only the task in `active_task_id` may be worked on. All output must reference this task.
3. **Legal status transitions.** Use only: `pending -> ready -> active`, `active -> claimed_done | blocked | failed`, `blocked -> ready | pending`. The engine enforces the full transition table.
4. **Evidence required for done.** `claimed_done` MUST include evidence in your `lhtm-update` block. Evidence = file paths, test results, or observations.
5. **Never touch `verified_done`.** This status is engine-owned. Do not propose it.
6. **Output `lhtm-update` every turn.** Every response must end with a valid `lhtm-update` fenced block.
7. **Stay in allowed paths.** Only read/write files under `allowed_paths` from the active task card.
8. **`definition_of_done` decides.** A task is done only when all items in its `definition_of_done` are satisfied with evidence.
9. **Propose, don't execute.** You propose actions in `proposed_actions`. The action gate validates them; the safe executor runs only approved actions. Never bypass the gate.
10. **Goal frozen.** The goal hash is checked every cycle. If the goal text changes, it is a mismatch - flag it, don't adapt.
