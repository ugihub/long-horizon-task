# LHTM v2 - Quickstart

Three ways to use LHTM v2.

## 1. Run the engine (Python 3.13+)

Install the only non-stdlib dependency, then run the supervised demo:

```bash
python -m pip install PyYAML
python scripts/run_supervised.py
```

Run the test suite (stdlib unittest):

```bash
python -m unittest discover -s tests
```

Run the P8 evaluation harness (writes eval/report.md, exit 0 = all targets met):

```bash
python -m eval
```

## 2. Install the skill pack (Claude Code / Antigravity / Codex)

When the repo is public, install the skills globally with skills.sh:

```bash
npx skills add ugihub/long-horizon-task
```

This installs six skills: `lhtm-core`, `planner`, `executor`, `verifier`,
`recovery`, `output-contract`. The model reads the SKILL.md rules and follows the
LHTM protocol - you chat normally, the skill drives plan/execute/verify/recover.

The engine itself is local Python. Skill clients cannot run Python; install the
engine on the machine doing the work (see path 1) and the skills drive the protocol.

## 3. Use LHTM in a skill client

1. Make sure the engine repo is checked out on the working machine.
2. Install the skills (path 2).
3. State your goal. The model plans (lhtm.plan/v1 JSON), executes one task at a
   time via `lhtm-update` blocks, and evidence gates `claimed_done`.
4. Default mode is `supervised` - writes and commands ask for your approval.

## Requirements

- Python 3.13+ (stdlib unittest for tests)
- PyYAML (only non-stdlib dependency, used by engine/lhtm/config.py)
