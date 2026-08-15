# LHTM v2 - Security

## Defaults

- Default execution mode is `supervised`: mutating actions (write, delete, run
  command) always require approval. DRY_RUN, AUTO_SAFE, and FULL_AUTO exist but
  are opt-in.
- `switch_to_safe_mode` can lower a mode but can never raise to FULL_AUTO.

## Action gate (deterministic, not prompts)

Every proposed action passes ActionGate before execution:
- Active task check - only `active_task_id` may act.
- Allowed paths - paths outside the task's `allowed_paths` are rejected.
- Sensitive blocklist - `.env`, `*.pem`, `*.key`, `secrets/`, `.lhtm/`, and
  credential paths are always blocked, regardless of allowed_paths.
- Destructive commands - `rm -rf`, `sudo`, `curl|bash`, `chmod 777`, force push,
  DROP DATABASE/TABLE are always rejected.
- Command allowlist - only configured tools (e.g. pytest, ruff) run; raw shell is
  not the default.

## Secret redaction

`redactor.py` redacts secrets (api_key, password, tokens, .pem content) in
model-facing output. Redaction is model-facing only - it never changes persisted
state, so verification still sees the raw evidence paths it needs.

## Prompt injection defense

External content is treated as untrusted. Injection defenses are enforced in the
engine (blocklists, deterministic gates), not left to prompt discipline.

## Runbooks

Runbooks are operator-authored, never LLM-proposed. The runner is idempotent,
times out per step, supports dry-run, backs up before changes, and stops on
failure.

## Trust model

FULL_AUTO is highest trust (no approval). Use it only with a fully scoped plan
and locked-down allowed_paths. The safe default is supervised.
