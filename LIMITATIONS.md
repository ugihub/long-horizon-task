# LHTM v2 - Limitations

Honest limits of the current release.

## Engine is local Python

The skill pack installs into any skill client (Claude Code, Antigravity, Codex),
but skill clients cannot execute Python. The engine must run on the machine
doing the work. The skills drive the protocol; the engine enforces it.

## No LLM baseline yet

task.md P8 "Baseline comparison A-E" (real LLM runs, low temperature, 3-5
runs/scenario) is deferred. The eval harness proves the deterministic guardrails
with static fixtures; it does not yet benchmark model behavior.

## Fixture scope

The 8 eval categories are representative, not exhaustive. New adversarial cases
belong in eval/fixtures/ and are locked by the expected-outcome checks.

## FULL_AUTO is trust, not safety

FULL_AUTO removes approval. It does not remove the gate - allowed paths,
blocklists, and destructive-command checks still apply - but it assumes the
plan's scope is correct.

## Windows console encoding

The engine emits ASCII-only output so Windows cp1252 consoles do not crash.
Markdown files themselves are UTF-8 and may hold any text.
