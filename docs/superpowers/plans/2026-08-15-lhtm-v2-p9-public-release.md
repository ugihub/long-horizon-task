# P9 Public Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prepare LHTM v2 for public release - skills.sh-convertible skill pack, ASCII hygiene, release docs, packaging (pyproject + LICENSE), CI workflows, and an example project. Repo stays PRIVATE; artifacts complete and verified.

**Architecture:** The repo already has two surfaces: the Python engine (`engine/lhtm/`, `eval/`) and a markdown skill pack (`skills/`). P9 packages both with zero engine-logic changes: convert `skills/` to 6 `skills/<name>/SKILL.md` with YAML frontmatter, sweep non-ASCII glyphs repo-wide, write 5 release docs, update README, add pyproject.toml + LICENSE (MIT) + 3 CI workflows, and add `example/`. Three new stdlib test files lock the invariants (skill frontmatter, repo ASCII, CI workflows).

**Tech Stack:** Python 3.13 stdlib, PyYAML (installed, 6.0.2), ruff (CI lint only), GitHub Actions (written, not executed while repo is private).

**Repo layout notes:** Engine code in `engine/lhtm/`. Tests use stdlib `unittest` (NOT pytest) - run with `python -m unittest discover -s tests -p "test_*.py"`. Currently 236 tests pass. Windows shell with limited PATH - use full paths:
- Python: `C:/Users/ugisu/AppData/Local/Programs/Python/Python313/python.exe`
- Git: `"C:/Program Files/Git/bin/git.exe"`
- Do NOT use `grep`, `tail`, `head`, `sed`, `tr`, `rm` on the shell - not on PATH. Use Python for file/stream ops.
- Commit directly to `main` (established project workflow). `eval/report.md` and `.lhtm/*` are gitignored.

**Existing context (read before implementing):**
- `skills/` currently flat: `executor.md, lhtm_core.md, output_contract.md, planner.md, recovery.md, verifier.md`. Three files have a corrupted `U+FFFD` char in their H1: `# Planner Skill [U+FFFD] LHTM Plan Generation`, `# Verifier Skill [U+FFFD] Evidence Verification`, `# Recovery Skill [U+FFFD] Error Recovery Actions`. Full current content of each is in the task below.
- Non-ASCII inventory (from a scan): `docs/superpowers/*` (em-dashes, arrows `->` unicode U+2192, `sec.` section sign U+00A7, checkmarks, box-drawing chars in diagrams), `task.md` (48 glyphs), `Implementation_plan.md` (413 glyphs incl. smart quotes + box-drawing diagrams), `policies/*` (em-dashes, arrows), `examples/task_card.md` (em-dashes). `engine/`, `eval/`, `scripts/` .py files are already ASCII-clean.
- `scripts/run_supervised.py` is the supervised demo - it does `sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))` so it already resolves the repo root from any two-levels-deep location, and writes `src/` to the CWD (then rmtree's it). Reused verbatim for `example/`.
- `.gitignore` exists (ignores `.lhtm/*` except `config.yaml`, `__pycache__`, `dist/build`, `eval/report.md`).
- PyYAML 6.0.2 installed. `tomllib` available (stdlib 3.11+) for pyproject verification.

**Constraint: ALL output ASCII.** No non-ASCII glyphs in code, comments, commit messages, or any file under `skills/`, `policies/`, `examples/`, `engine/`, `eval/`, `scripts/`, `example/`, or top-level `*.md`. Windows cp1252 console. Use `->` (ASCII hyphen + greater-than) for arrows. Historical design docs under `docs/superpowers/` and `Implementation_plan.md` are EXEMPT from the full-ASCII gate but must have no `U+2192` arrows or `U+FFFD` corruption (see Task 2).

---

### Task 1: Skill pack conversion - 6 `skills/<name>/SKILL.md`

**Files:**
- Create: `tests/test_skills.py`
- Create: `skills/lhtm-core/SKILL.md`
- Create: `skills/planner/SKILL.md`
- Create: `skills/executor/SKILL.md`
- Create: `skills/verifier/SKILL.md`
- Create: `skills/recovery/SKILL.md`
- Create: `skills/output-contract/SKILL.md`
- Delete: `skills/lhtm_core.md`, `skills/planner.md`, `skills/executor.md`, `skills/verifier.md`, `skills/recovery.md`, `skills/output_contract.md`

**Purpose:** Convert the flat skill pack to the skills.sh format (`skills/<name>/SKILL.md` + YAML frontmatter with `name` + `description`), which is what `npx skills add ugihub/long-horizon-task` installs into Claude Code / Antigravity / Codex. Each body is the existing content, ASCII-clean, with the corrupted `U+FFFD` chars fixed and a `Requires:` cross-reference to `lhtm-core`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_skills.py`:

```python
# tests/test_skills.py
import os
import sys
import unittest

import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = os.path.join(ROOT, "skills")
EXPECTED = {"lhtm-core", "planner", "executor", "verifier", "recovery", "output-contract"}


def _frontmatter(path):
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    if lines[:1] != ["---"]:
        return None
    end = lines[1:].index("---") + 1
    return yaml.safe_load("\n".join(lines[1:end]))


class TestSkills(unittest.TestCase):
    def test_six_skill_dirs(self):
        dirs = {d for d in os.listdir(SKILLS) if os.path.isdir(os.path.join(SKILLS, d))}
        self.assertEqual(dirs, EXPECTED)

    def test_each_skill_has_valid_frontmatter(self):
        for name in EXPECTED:
            p = os.path.join(SKILLS, name, "SKILL.md")
            self.assertTrue(os.path.isfile(p), f"{name}: SKILL.md missing")
            fm = _frontmatter(p)
            self.assertIsNotNone(fm, f"{name}: missing frontmatter")
            self.assertIn("name", fm, f"{name}: missing name")
            self.assertIn("description", fm, f"{name}: missing description")
            self.assertEqual(fm["name"], name, f"{name}: frontmatter name mismatch")
            self.assertIsInstance(fm["description"], str)
            self.assertTrue(fm["description"].strip(), f"{name}: empty description")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `C:/Users/ugisu/AppData/Local/Programs/Python/Python313/python.exe -m unittest tests.test_skills -v`
Expected: FAIL - dirs set is empty, mismatch with EXPECTED.

- [ ] **Step 3: Create the 6 SKILL.md files (replace flat files)**

Create `skills/lhtm-core/SKILL.md`:

```markdown
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
```

Create `skills/planner/SKILL.md`:

```markdown
---
name: planner
description: Generate a JSON plan (schema lhtm.plan/v1) from a goal.
---

# Planner Skill - LHTM Plan Generation

Requires: `lhtm-core` (the 10 non-negotiable rules apply).

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
```

Create `skills/executor/SKILL.md`:

```markdown
---
name: executor
description: Per-turn execution for one active task, proposing lhtm-update blocks and evidence.
---

# Executor Skill - Per-Turn Execution

Requires: `lhtm-core` (the 10 non-negotiable rules apply). Emits `output-contract` blocks.

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
```

Create `skills/verifier/SKILL.md`:

```markdown
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
```

Create `skills/recovery/SKILL.md`:

```markdown
---
name: recovery
description: Choose a recovery action when a task fails or the system enters RECOVERY phase.
---

# Recovery Skill - Error Recovery Actions

Requires: `lhtm-core` (the 10 non-negotiable rules apply).

When a task fails or the system enters `RECOVERY` phase, choose one:

| Action | When | How |
|--------|------|-----|
| `retry_with_hint` | Output error, next attempt available | Set status `active`, include hint |
| `decompose_task` | Task too large, keeps failing | Split into sub-tasks, update plan |
| `request_user_input` | Need human decision | Set phase `WAITING_USER`, ask question |
| `mark_blocked` | External dependency missing | Set status `blocked`, record reason |
| `rollback_proposal` | Changes need undoing | Propose restore from snapshot |
| `switch_to_safe_mode` | Repeated failures, risk | Switch mode to `DRY_RUN` or `SUPERVISED` |

## Rules
- Max retries before escalation: `max_attempts` (default 3)
- After 2 consecutive failures, suggest `decompose_task` or `request_user_input`
- Never silently retry the same failing action
```

Create `skills/output-contract/SKILL.md`:

```markdown
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
```

- [ ] **Step 4: Delete the flat skill files**

Use Python (no `rm` on PATH):

```python
import os
for f in ["lhtm_core.md", "planner.md", "executor.md", "verifier.md", "recovery.md", "output_contract.md"]:
    p = os.path.join("skills", f)
    if os.path.exists(p):
        os.remove(p)
        print("removed", p)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `C:/Users/ugisu/AppData/Local/Programs/Python/Python313/python.exe -m unittest tests.test_skills -v`
Expected: PASS (2 tests).

- [ ] **Step 6: Verify flat files gone + no non-ASCII in skills/**

Run: `C:/Users/ugisu/AppData/Local/Programs/Python/Python313/python.exe -c "import os,glob; print('SKILL.md files:', glob.glob('skills/*/SKILL.md')); print('flat remain:', [f for f in os.listdir('skills') if f.endswith('.md')])"`
Expected: 6 SKILL.md files, 0 flat .md. Also confirm each SKILL.md is ASCII-only (no glyph > 127).

- [ ] **Step 7: Run full suite**

Run: `C:/Users/ugisu/AppData/Local/Programs/Python/Python313/python.exe -m unittest discover -s tests -p "test_*.py"`
Expected: 238 pass (236 + 2). If the count differs, report the actual number.

- [ ] **Step 8: Commit**

```bash
"C:/Program Files/Git/bin/git.exe" add skills tests/test_skills.py
"C:/Program Files/Git/bin/git.exe" commit -m "feat(p9): convert skill pack to skills.sh SKILL.md format"
```

---

### Task 2: ASCII hygiene sweep + regression lock

**Files:**
- Create: `scripts/ascii_sweep.py`
- Create: `tests/test_release_ascii.py`

**Purpose:** Mechanically convert non-ASCII glyphs to ASCII repo-wide (fixing the corrupted `U+FFFD` chars is done in Task 1 via the new SKILL.md bodies), then lock it with a test. Scope decision: box-drawing block chars (U+2500-257F) and smart quotes (U+2018-201F) in historical design docs are PRESERVED (converting them mangles diagrams and quoted samples); everything else converts. `docs/superpowers/` + `Implementation_plan.md` are exempt from the full-ASCII gate but must have no `U+2192` arrows or `U+FFFD`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_release_ascii.py`:

```python
# tests/test_release_ascii.py
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# dirs that must be fully ASCII (they ship to skill clients or are engine-facing)
REQUIRED_ASCII_DIRS = ["skills", "policies", "examples", "engine", "eval", "scripts", "example"]
# dirs/file exempt from the full-ASCII gate (historical editorial + diagrams)
SKIP = (".git", ".lhtm", ".pytest_cache", "__pycache__", "eval/report.md")


def _rel(p):
    return os.path.relpath(p, ROOT).replace(os.sep, "/")


class TestReleaseAscii(unittest.TestCase):
    def test_required_dirs_are_ascii(self):
        bad = []
        for d in REQUIRED_ASCII_DIRS:
            base = os.path.join(ROOT, d)
            if not os.path.isdir(base):
                continue  # dir not created yet (e.g. example/ before Task 7)
            for root, _, files in os.walk(base):
                for f in files:
                    p = os.path.join(root, f)
                    try:
                        txt = open(p, encoding="utf-8").read()
                    except (OSError, UnicodeDecodeError):
                        continue
                    hits = [(i + 1, ch) for i, ch in enumerate(txt) if ord(ch) > 127]
                    if hits:
                        bad.append((_rel(p), hits[:3]))
        self.assertEqual(bad, [], f"non-ASCII in required dirs: {bad[:5]}")

    def test_no_arrows_or_corruption_anywhere(self):
        bad = []
        for root, dirs, files in os.walk(ROOT):
            dirs[:] = [d for d in dirs if d not in SKIP]
            for f in files:
                p = os.path.join(root, f)
                rel = _rel(p)
                if rel == "eval/report.md":
                    continue
                try:
                    txt = open(p, encoding="utf-8").read()
                except (OSError, UnicodeDecodeError):
                    continue
                for i, ch in enumerate(txt):
                    if ord(ch) in (0x2192, 0xFFFD):
                        bad.append((rel, i + 1, "U+%04X" % ord(ch)))
                        break
        self.assertEqual(bad, [], f"arrows or corruption: {bad[:5]}")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `C:/Users/ugisu/AppData/Local/Programs/Python/Python313/python.exe -m unittest tests.test_release_ascii -v`
Expected: FAIL - both tests report non-ASCII in `policies/`, `examples/`, `task.md`, `Implementation_plan.md`, `docs/superpowers/`.

- [ ] **Step 3: Write the sweep script**

Create `scripts/ascii_sweep.py`:

```python
# scripts/ascii_sweep.py
"""Repo-wide ASCII hygiene sweep (P9). Converts common non-ASCII glyphs to ASCII.

Preserves box-drawing block chars (U+2500-257F) and smart quotes (U+2018-201F),
which appear in historical design diagrams and quoted samples where conversion
would mangle content. Run once, review the diff, then the test suite locks it.
"""
import os

REPLACEMENTS = {
    "sec.": "sec.",    # section sign
    "-": "-",       # en dash
    "--": "--",      # em dash
    "->": "->",      # right arrow
    ">": ">",       # black right-pointing triangle
    "v": "v",       # black down-pointing triangle
    "[x]": "[x]",     # white heavy check mark (button)
    "[x]": "[x]",     # check mark
}

SKIP_DIRS = {".git", ".lhtm", ".pytest_cache", "__pycache__"}
SKIP_FILES = {"eval/report.md"}


def _skipped(rel: str) -> bool:
    return rel == "eval/report.md"


def sweep(root: str = ".") -> list:
    changed = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            p = os.path.join(dirpath, fn)
            rel = os.path.relpath(p, root).replace(os.sep, "/")
            if _skipped(rel):
                continue
            try:
                with open(p, encoding="utf-8") as f:
                    txt = f.read()
            except (OSError, UnicodeDecodeError):
                continue
            out = []
            for ch in txt:
                code = ord(ch)
                if 0x2500 <= code <= 0x257F or 0x2018 <= code <= 0x201F:
                    out.append(ch)  # preserve box-drawing + smart quotes
                else:
                    out.append(REPLACEMENTS.get(ch, ch))
            new = "".join(out)
            if new != txt:
                with open(p, "w", encoding="utf-8", newline="") as f:
                    f.write(new)
                changed.append(rel)
    return changed


if __name__ == "__main__":
    changed = sweep()
    print(f"ASCII sweep: {len(changed)} files changed")
    for c in sorted(changed):
        print("  ", c)
```

- [ ] **Step 4: Run the sweep**

Run: `C:/Users/ugisu/AppData/Local/Programs/Python/Python313/python.exe scripts/ascii_sweep.py`
Expected: prints a list of changed files under `docs/`, `policies/`, `examples/`, `task.md`, `Implementation_plan.md` (arrows, dashes, section signs, checkmarks converted; box-drawing + smart quotes preserved). `skills/` should already be clean from Task 1.

- [ ] **Step 5: Verify the sweep did not mangle critical content**

Run: `C:/Users/ugisu/AppData/Local/Programs/Python/Python313/python.exe -c "import sys; sys.stdout.reconfigure(encoding='utf-8'); print(open('policies/completion_rules.md', encoding='utf-8').read()[:200])"`
Expected: `->` arrows in place of unicode arrows; no U+FFFD. Spot-check `task.md` too.

- [ ] **Step 6: Run test to verify it passes**

Run: `C:/Users/ugisu/AppData/Local/Programs/Python/Python313/python.exe -m unittest tests.test_release_ascii -v`
Expected: PASS (2 tests). NOTE: `docs/superpowers/` and `Implementation_plan.md` may still contain em-dashes/smart-quotes/box-drawing (exempt) - the second test only checks for arrows + corruption, which the sweep removed.

- [ ] **Step 7: Run full suite + confirm repo tests still green**

Run: `C:/Users/ugisu/AppData/Local/Programs/Python/Python313/python.exe -m unittest discover -s tests -p "test_*.py"`
Expected: 240 pass (238 + 2). If any existing test broke (e.g. a test fixture asserting a non-ASCII string), fix the test to the ASCII form. Report actual count.

- [ ] **Step 8: Commit**

```bash
"C:/Program Files/Git/bin/git.exe" add scripts/ascii_sweep.py tests/test_release_ascii.py docs policies examples task.md Implementation_plan.md
"C:/Program Files/Git/bin/git.exe" commit -m "chore(p9): ASCII hygiene sweep + release ascii regression test"
```

---

### Task 3: Release documentation (5 files)

**Files:**
- Create: `QUICKSTART.md`
- Create: `ARCHITECTURE.md`
- Create: `SECURITY.md`
- Create: `LIMITATIONS.md`
- Create: `EVALUATION.md`

**Purpose:** The task.md P9 documentation deliverable. Each file is ASCII-only, concise, and accurate to the actual engine behavior (verified against the code in prior tasks).

- [ ] **Step 1: Create `QUICKSTART.md`**

```markdown
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
```

- [ ] **Step 2: Create `ARCHITECTURE.md`**

```markdown
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
```

- [ ] **Step 3: Create `SECURITY.md`**

```markdown
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
```

- [ ] **Step 4: Create `LIMITATIONS.md`**

```markdown
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
```

- [ ] **Step 5: Create `EVALUATION.md`**

```markdown
# LHTM v2 - Evaluation

P8 delivers a deterministic evaluation harness (eval/). Run it:

```bash
python -m eval
```

Writes eval/report.md; exit code 0 iff every metric meets its target.

## Metrics vs targets (task.md P8)

| Metric | Target | Result |
|---|---|---|
| schema_valid_rate | > 0.98 | 1.000 |
| false_completion | < 0.05 | 0.000 |
| out_of_scope | == 0 (escapes) | 0.000 |
| secret_leak | == 0 (escapes) | 0.000 |
| test_pass | > 0.70 | 1.000 |

The security metrics count ESCAPES (gate-rejected actions that were nevertheless
executed), not attempts: a blocked out-of-scope write is the guardrail working.

## Scenario categories (8)

1. linear - happy path, two dependent tasks
2. branch - two tasks with a dependency chain
3. high-risk - approval required for high-risk command
4. verify-fail - fake evidence (file never created) -> failed
5. recovery - retry_with_hint after failed verification -> pass
6. secret-leak - write to .env blocked
7. out-of-scope - write outside allowed_paths blocked
8. destructive - `rm -rf` rejected

Every fixture's outcome is locked to its `expected` block: a gate or verifier
regression flips `passed` to false and the harness exits 1.
```

- [ ] **Step 6: Verify all 5 docs ASCII-only + consistent**

Run: `C:/Users/ugisu/AppData/Local/Programs/Python/Python313/python.exe -c "import sys; sys.stdout.reconfigure(encoding='utf-8'); [print(f, [hex(ord(c)) for c in open(f,encoding='utf-8').read() if ord(c)>127][:3]) for f in ['QUICKSTART.md','ARCHITECTURE.md','SECURITY.md','LIMITATIONS.md','EVALUATION.md']]"`
Expected: each prints `[]` (no non-ASCII).

- [ ] **Step 7: Run full suite**

Run: `C:/Users/ugisu/AppData/Local/Programs/Python/Python313/python.exe -m unittest discover -s tests -p "test_*.py"`
Expected: 240 pass (docs only, no test change).

- [ ] **Step 8: Commit**

```bash
"C:/Program Files/Git/bin/git.exe" add QUICKSTART.md ARCHITECTURE.md SECURITY.md LIMITATIONS.md EVALUATION.md
"C:/Program Files/Git/bin/git.exe" commit -m "docs(p9): release documentation (quickstart, architecture, security, limitations, evaluation)"
```

---

### Task 4: README update

**Files:**
- Modify: `README.md`

**Purpose:** Update the existing bilingual README: roadmap P8+P9 done, add a skills.sh install section, and mention `example/`.

- [ ] **Step 1: Update the README roadmap section**

The README is bilingual (English + Bahasa Indonesia). In BOTH language sections, update the "Roadmap status" / "Status roadmap" paragraph. Replace the current text (which says P8 and P9 are "not yet implemented" / "belum diimplementasikan") with a "Done" statement, and add a short "Install the skills" / "Pasang skill" subsection right after the "Quick start" / "Memulai cepat" sections.

English roadmap (replace the paragraph that currently ends `P9 (public release) are not yet implemented.`):

```markdown
### Roadmap status

All sprints P0-P9 implemented: skill pack + output contract, stateful planning,
supervised executor, evidence verification, safe command execution, recovery &
robustness, security & context hardening, evaluation harness (P8), and public
release packaging (P9). Install the skill pack in Claude Code / Antigravity /
Codex with `npx skills add ugihub/long-horizon-task` (once the repo is public).
The repo is currently private; all release artifacts are present and verified.
```

English install subsection (insert after the "Run the tests" block, before "Using the engine programmatically"):

```markdown
### Install the skills

Install the six LHTM skills into any skill client (Claude Code, Antigravity,
Codex):

```bash
npx skills add ugihub/long-horizon-task
```

The engine is local Python; see `QUICKSTART.md` for the three usage paths.
```

Bahasa roadmap (replace the paragraph that currently ends `P9 (public release) belum diimplementasikan.`):

```markdown
### Status roadmap

Semua sprint P0-P9 sudah diimplementasikan: skill pack + kontrak output, planning
ber-state, executor supervised, verifikasi bukti, eksekusi perintah aman, recovery
& ketangguhan, penguatan keamanan & konteks, evaluation harness (P8), dan
packaging rilis publik (P9). Pasang skill pack di Claude Code / Antigravity /
Codex dengan `npx skills add ugihub/long-horizon-task` (setelah repo publik).
Saat ini repo masih privat; semua artefak rilis sudah lengkap dan terverifikasi.
```

Bahasa install subsection (insert after the "Jalankan tes" block, before "Memakai engine secara programatik"):

```markdown
### Pasang skill

Pasang enam skill LHTM ke klien skill apa pun (Claude Code, Antigravity, Codex):

```bash
npx skills add ugihub/long-horizon-task
```

Engine adalah Python lokal; lihat `QUICKSTART.md` untuk tiga jalur pemakaian.
```

- [ ] **Step 2: Update the repository layout section**

In the repo layout code block (both languages), add the new top-level entries after the `eval/` line (if present) or after `scripts/`:

```text
example/                Standalone supervised demo (example project)
QUICKSTART.md           Three usage paths
ARCHITECTURE.md         Component + data-flow overview
SECURITY.md             Security model and defaults
LIMITATIONS.md          Honest limits of the release
EVALUATION.md           P8 evaluation results and how to rerun
pyproject.toml          Packaging metadata (no install needed to use)
LICENSE                 MIT
.github/workflows/      CI: test, lint, eval
```

- [ ] **Step 3: Verify the README remains valid + bilingual structure intact**

Run: `C:/Users/ugisu/AppData/Local/Programs/Python/Python313/python.exe -c "import sys; sys.stdout.reconfigure(encoding='utf-8'); t=open('README.md',encoding='utf-8').read(); assert 'Bahasa Indonesia' in t and 'English' in t; print('README bilingual OK, lines:', len(t.splitlines()))"`
Expected: `README bilingual OK, lines: <N>` (the file still has both language sections).

- [ ] **Step 4: Run full suite**

Run: `C:/Users/ugisu/AppData/Local/Programs/Python/Python313/python.exe -m unittest discover -s tests -p "test_*.py"`
Expected: 240 pass (docs only).

- [ ] **Step 5: Commit**

```bash
"C:/Program Files/Git/bin/git.exe" add README.md
"C:/Program Files/Git/bin/git.exe" commit -m "docs(p9): README roadmap done + skills install section"
```

---

### Task 5: pyproject.toml + LICENSE

**Files:**
- Create: `pyproject.toml`
- Create: `LICENSE`

**Purpose:** task.md P9 packaging. pyproject is metadata + dev-deps only (no console scripts - the engine runs via python path). LICENSE is MIT.

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "lhtm-v2"
version = "0.1.0"
description = "Deterministic engine for safe, verifiable long-horizon agentic tasks."
readme = "README.md"
requires-python = ">=3.13"
license = "MIT"
authors = [{ name = "ugihub" }]
keywords = ["llm", "agents", "guardrails", "task-management", "evaluation"]
classifiers = [
  "Programming Language :: Python :: 3",
  "Programming Language :: Python :: 3.13",
  "License :: OSI Approved :: MIT License",
]

[project.optional-dependencies]
dev = ["PyYAML>=6.0", "ruff>=0.4"]

[tool.ruff]
line-length = 100

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
```

- [ ] **Step 2: Create `LICENSE`**

```text
MIT License

Copyright (c) 2026 ugihub

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

- [ ] **Step 3: Verify pyproject parses + README/license consistent**

Run: `C:/Users/ugisu/AppData/Local/Programs/Python/Python313/python.exe -c "import tomllib; d=tomllib.load(open('pyproject.toml','rb')); print('pyproject OK:', d['project']['name'], d['project']['version']); print('license:', d['project']['license'])"`
Expected: `pyproject OK: lhtm-v2 0.1.0` and `license: MIT`.

- [ ] **Step 4: Verify suite still green + ruff config valid**

Run full suite (expect 240 pass). Then `C:/Users/ugisu/AppData/Local/Programs/Python/Python313/python.exe -c "import yaml; print('yaml OK', yaml.__version__)"` to confirm dev-dep availability.

- [ ] **Step 5: Commit**

```bash
"C:/Program Files/Git/bin/git.exe" add pyproject.toml LICENSE
"C:/Program Files/Git/bin/git.exe" commit -m "chore(p9): packaging metadata (pyproject) + MIT license"
```

---

### Task 6: CI workflows + regression test

**Files:**
- Create: `.github/workflows/test.yml`
- Create: `.github/workflows/lint.yml`
- Create: `.github/workflows/eval.yml`
- Create: `tests/test_release_ci.py`

**Purpose:** task.md P9 CI. Written and YAML-valid now; executed once the repo is public (Actions needs a remote). A test locks the three files exist and parse.

- [ ] **Step 1: Write the failing test**

Create `tests/test_release_ci.py`:

```python
# tests/test_release_ci.py
import os
import sys
import unittest

import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WF = os.path.join(ROOT, ".github", "workflows")
WORKFLOWS = ("test.yml", "lint.yml", "eval.yml")


class TestReleaseCi(unittest.TestCase):
    def test_workflows_exist(self):
        for name in WORKFLOWS:
            self.assertTrue(os.path.isfile(os.path.join(WF, name)), f"missing {name}")

    def test_workflows_parse_and_have_jobs(self):
        for name in WORKFLOWS:
            with open(os.path.join(WF, name), encoding="utf-8") as f:
                data = yaml.safe_load(f)
            self.assertIsInstance(data, dict, name)
            self.assertIn("name", data, name)
            self.assertIn("on", data, name)
            self.assertIn("jobs", data, name)
            self.assertTrue(data["jobs"], f"{name}: no jobs")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `C:/Users/ugisu/AppData/Local/Programs/Python/Python313/python.exe -m unittest tests.test_release_ci -v`
Expected: FAIL - files missing.

- [ ] **Step 3: Create the three workflows**

Create `.github/workflows/test.yml`:

```yaml
name: test

on:
  push:
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
      - run: python -m pip install PyYAML
      - run: python -m unittest discover -s tests
```

Create `.github/workflows/lint.yml`:

```yaml
name: lint

on:
  push:
  pull_request:

jobs:
  ruff:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
      - run: python -m pip install ruff
      - run: ruff check engine eval scripts
```

Create `.github/workflows/eval.yml`:

```yaml
name: eval

on:
  push:
  pull_request:

jobs:
  eval:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
      - run: python -m pip install PyYAML
      - run: python -m eval
      - run: test -f eval/report.md
      - uses: actions/upload-artifact@v4
        with:
          name: eval-report
          path: eval/report.md
```

- [ ] **Step 4: Run test to verify it passes**

Run: `C:/Users/ugisu/AppData/Local/Programs/Python/Python313/python.exe -m unittest tests.test_release_ci -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Run full suite**

Run: `C:/Users/ugisu/AppData/Local/Programs/Python/Python313/python.exe -m unittest discover -s tests -p "test_*.py"`
Expected: 242 pass (240 + 2). Report actual count.

- [ ] **Step 6: Commit**

```bash
"C:/Program Files/Git/bin/git.exe" add .github/workflows tests/test_release_ci.py
"C:/Program Files/Git/bin/git.exe" commit -m "ci(p9): test, lint, eval workflows + regression test"
```

---

### Task 7: example project

**Files:**
- Create: `example/run_supervised_demo.py`
- Create: `example/README.md`

**Purpose:** task.md P9 "Example project + run_supervised_demo.py". The demo is the canonical supervised driver, copied into `example/` as a standalone example (it already resolves the repo root via `sys.path.insert` two levels up and cleans up its `src/` writes).

- [ ] **Step 1: Copy the demo into example/**

Copy `scripts/run_supervised.py` to `example/run_supervised_demo.py` byte-for-byte, then edit ONLY the header docstring (first line) to:

```python
# example/run_supervised_demo.py
"""LHTM v2 example project: end-to-end supervised demo (P3+P4), ASCII output.

A copy of scripts/run_supervised.py for the example/ project. Run it from the
repo root or from example/ - it writes temp work + src/ relative to the CWD and
cleans both up. Simulates an LLM with canned lhtm-update blocks; the action gate
+ safe executor + engine verifier do the real work. No LLM API.
"""
```

Copy the rest of the file unchanged (the `simulate_llm`, `main`, imports, and `if __name__ == "__main__"` blocks stay identical). Note: `sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))` in the original already resolves the repo root when the file lives in `example/`.

- [ ] **Step 2: Create `example/README.md`**

```markdown
# LHTM v2 - Example Project

A standalone supervised demo. It drives the real engine (action gate + safe
executor + evidence verifier + recovery) with a simulated LLM - no API, no cost.

## Run

```bash
python example/run_supervised_demo.py
```

## What it shows

- T01 and T02 reach `verified_done` (evidence verified, files written).
- T03 claims a file that was never created -> verification fails.
- Recovery drives T03 through `retry_with_hint` then `mark_blocked`.
- A redacted progress tracker is rendered at the end.

The demo writes `src/` relative to the current working directory and removes it
when done. The engine state lives in a temp `.lhtm` dir, also removed.

## Source

The demo is a copy of `scripts/run_supervised.py`. Keep them in sync if you
change the driver logic.
```

- [ ] **Step 3: Verify the demo runs**

Run: `C:/Users/ugisu/AppData/Local/Programs/Python/Python313/python.exe example/run_supervised_demo.py`
Expected: prints the goal, plan approved, per-step engine updates, recovery lines, the redacted tracker, and ends with `V Supervised Tahap 2+3+4 demo passed!`. Exit 0.

- [ ] **Step 4: Verify no repo pollution**

Run: `C:/Users/ugisu/AppData/Local/Programs/Python/Python313/python.exe -c "import os; print([d for d in os.listdir('.') if d in ('src','etc')])"`
Expected: `[]` (demo cleaned up its `src/`).

- [ ] **Step 5: Run full suite**

Run: `C:/Users/ugisu/AppData/Local/Programs/Python/Python313/python.exe -m unittest discover -s tests -p "test_*.py"`
Expected: 242 pass (docs/data only; the release_ascii test now also covers `example/`).

- [ ] **Step 6: Commit**

```bash
"C:/Program Files/Git/bin/git.exe" add example/run_supervised_demo.py example/README.md
"C:/Program Files/Git/bin/git.exe" commit -m "feat(p9): example project (standalone supervised demo)"
```

---

### Task 8: task.md P9 checkboxes + final verification

**Files:**
- Modify: `task.md`

**Purpose:** Mark the P9 section complete (verifying each deliverable exists) and run the final end-to-end verification.

- [ ] **Step 1: Verify every P9 deliverable exists**

Run: `C:/Users/ugisu/AppData/Local/Programs/Python/Python313/python.exe -c "
import os
checks = {
  'skills.sh dirs': sorted(d for d in os.listdir('skills') if os.path.isdir(os.path.join('skills', d))),
  'docs': [f for f in ['README.md','QUICKSTART.md','ARCHITECTURE.md','SECURITY.md','LIMITATIONS.md','EVALUATION.md'] if os.path.isfile(f)],
  'example': os.path.isfile('example/run_supervised_demo.py'),
  'ci': sorted(os.listdir('.github/workflows')) if os.path.isdir('.github/workflows') else [],
  'pyproject': os.path.isfile('pyproject.toml'),
  'license': os.path.isfile('LICENSE'),
}
print(checks)
"`
Expected: 6 skill dirs, all 6 docs present, example True, 3 workflow files, pyproject + license True.

- [ ] **Step 2: Tick the P9 checkboxes in task.md**

In `task.md`, the `## P9 - Public Release (Milestone 7)` section has 6 unchecked items (`- [ ]`). Change each to `- [x]`. The items are: repositori final; README/QUICKSTART/ARCHITECTURE/SECURITY/LIMITATIONS/EVALUATION; example project + run_supervised_demo.py; CI workflows; pyproject.toml/LICENSE; default supervised + no critical security issue. (Verify the "default supervised" item against `engine/lhtm/config.py` DEFAULT_CONFIG before ticking.)

- [ ] **Step 3: Final full verification**

Run:
1. `C:/Users/ugisu/AppData/Local/Programs/Python/Python313/python.exe -m unittest discover -s tests -p "test_*.py"` - expect 242 pass.
2. `C:/Users/ugisu/AppData/Local/Programs/Python/Python313/python.exe -m eval` - expect `P8 eval: 8 cases, passed=True`, exit 0.
3. `C:/Users/ugisu/AppData/Local/Programs/Python/Python313/python.exe example/run_supervised_demo.py` - expect the demo finishes clean.
4. `C:/Users/ugisu/AppData/Local/Programs/Python/Python313/python.exe -m unittest tests.test_release_ascii tests.test_skills tests.test_release_ci -v` - expect 6 tests pass (release locks).

- [ ] **Step 4: Commit**

```bash
"C:/Program Files/Git/bin/git.exe" add task.md
"C:/Program Files/Git/bin/git.exe" commit -m "docs(p9): mark P9 release complete in task.md"
```

- [ ] **Step 5: Confirm final tree + clean working dir**

Run: `"C:/Program Files/Git/bin/git.exe" status --short`
Expected: clean (only `eval/report.md` gitignored). Report the final commit log (`git log --oneline -15`) and total test count in your report.

---

## Spec Self-Review

- **Spec coverage:** skill conversion (Task 1); ASCII hygiene + lock (Task 2); 5 release docs (Task 3); README update (Task 4); pyproject + LICENSE (Task 5); 3 CI workflows + lock (Task 6); example project (Task 7); task.md P9 tick + final verify (Task 8). Spec section 4.1-4.5 all mapped. Success criteria (Section 6) each covered by a task or the Task 8 final verification.
- **Placeholder scan:** every SKILL.md, doc, workflow, and toml/LICENSE is fully written; no TBD. Doc bodies written verbatim.
- **Type consistency:** frontmatter `name` values in Task 1 (`lhtm-core`, `planner`, `executor`, `verifier`, `recovery`, `output-contract`) match `EXPECTED` in `tests/test_skills.py` and the `npx skills add` claim in QUICKSTART. CI commands (`python -m unittest discover -s tests`, `python -m eval`, `ruff check engine eval scripts`) match the actual repo test/eval commands. The `example/run_supervised_demo.py` sys.path logic is verified against the source copy in Task 7.
- **Design corrections vs spec:** (1) ASCII hygiene scoped to preserve box-drawing block chars and smart quotes in historical design docs (converting them mangles diagrams) - `docs/superpowers/` and `Implementation_plan.md` are exempt from the full-ASCII gate but must be arrow/corruption-free; (2) test-count estimates (236 -> 242) are drift-tolerant as in prior plans.
