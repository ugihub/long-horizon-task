# LHTM v2 - Architecture

## Core principle

LLM proposes. Engine validates. Evidence decides.

The model never sets its own verdict. Every state transition, file write, and
command passes deterministic checks in the engine before anything is applied.
`verified_done` is engine-owned: a task reaches it only when the evidence
verifier proves the definition of done.

## Data flow

1. Goal -> hash (frozen, checked every cycle).
2. Planner proposes a plan (JSON, schema lhtm.plan/v1). Engine validates schema,
   task fields, dependencies, cycle-free, goal_hash match.
3. Plan approved -> phase READY.
4. Scheduler picks a ready task; exactly one `active_task_id` at a time.
5. Executor proposes an `lhtm-update` block with optional `proposed_actions`.
   ActionGate checks: active task, allowed paths, sensitive blocklist,
   destructive patterns, command allowlist. SafeExecutor runs approved actions.
6. `claimed_done` -> EvidenceVerifier checks C1-C5 (evidence present, paths
   allowed, files exist, definition of done covered, test evidence). Pass ->
   `verified_done`; fail -> `failed` + feedback.
7. Recovery actions (retry, decompose, mark blocked, etc.) move failed tasks
   through legal transitions.

## Canonical state

- `state.json` is the single source of truth (JSON canonical). Markdown trackers
  are generated views. The engine writes atomically under a lock.

## Components (engine/lhtm/)

- engine.py - LhtmEngine facade (goal, plan, activate, recover, facts)
- state_store.py - atomic state read/write + snapshots
- schema_validator.py - state/plan/update/transition validation
- task_scheduler.py - picks the next runnable task
- action_gate.py - security core: path/command/approval checks
- safe_executor.py - executes approved actions safely
- evidence_verifier.py - pass/fail on claimed_done evidence
- recovery.py - engine-orchestrated recovery actions
- redactor.py - deterministic secret redaction (model-facing only)
- runbook.py - declarative runbook runner (operator-authored)
- context_budget.py - budgeted hierarchical context assembly
- project_facts.py - read-only repo scan -> facts + excerpts
- markdown_view.py - renders progress tracker from state
- config.py - policy + allowlist (PyYAML, deep merge)

## Evaluation (eval/)

A static-fixture harness runs the real engine (gate + executor + verifier +
recovery) with no LLM. Produces 5 metrics vs task.md targets and eval/report.md.

## Skill pack (skills/)

Six SKILL.md files installable via skills.sh: lhtm-core (10 rules), planner,
executor, verifier, recovery, output-contract. Skills are markdown protocol; the
engine enforces it deterministically.
