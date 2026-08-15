# LHTM v2 - P9 Public Release Design

> **Agentic workers:** After approval, implementation proceeds via writing-plans -> subagent-driven-development.

**Date:** 2026-08-15
**Status:** Draft for user review

---

## 1. Goal

Prepare LHTM v2 for public release: repo stays PRIVATE, but every release artifact is
complete and verified. Deliverables per task.md P9: final repo layout, the six
documentation files, an example project, CI workflows, pyproject.toml + LICENSE,
skills.sh-convertible skill pack, and an ASCII-hygiene cleanup.

```
Release artifacts complete + verified now. Publish (make repo public) later.
No functional engine changes. Only packaging, docs, CI, skill-format conversion.
```

## 2. Non-Goals (defer)

- **Making the repo public / publishing** - user chose "stay private for now". All
  artifacts prepared; visibility toggle is a later one-line decision.
- **`npx skills add ugihub/long-horizon-task` verification** - cannot run while repo is
  private (skills.sh needs a public repo). Verifiable the moment it is published.
- **Pip-installable package with console scripts** - pyproject is metadata + dev deps
  only; no `[project.scripts]`. The engine runs via `python path` imports today.
- **LLM baseline comparison A-E** (task.md P8 Phase 12.2) - still deferred; documented
  in LIMITATIONS.md.
- **Splitting the repo into engine/ vs skill/ sub-packages** - single repo serves both
  use modes; documented in QUICKSTART.

## 3. Architecture

LHTM already has two surfaces. P9 only packages them:

```
Surface 1: Engine (Python)        Surface 2: Skill pack (markdown)
  engine/lhtm/* (20 modules)        skills/<name>/SKILL.md x6
  eval/ (P8 harness + fixtures)     installable via npx skills add <owner>/<repo>
  scripts/, example/                consumed by Claude Code / Antigravity / Codex
```

Release polish applied to BOTH: ASCII hygiene, docs, CI, packaging. No engine logic
changes.

## 4. Component Contracts

### 4.1 Skill pack conversion - `skills/<name>/SKILL.md`

Six sub-skills, each in its own directory with a `SKILL.md` carrying YAML frontmatter
(name + description). Flat `skills/*.md` files are deleted.

```
skills/
  lhtm-core/SKILL.md      # 10 non-negotiable rules (base; imported by all)
  planner/SKILL.md        # goal -> JSON plan lhtm.plan/v1
  executor/SKILL.md       # per-turn lhtm-update, one active task
  verifier/SKILL.md       # evidence -> verdict (second pass)
  recovery/SKILL.md       # recovery actions: retry/decompose/mark_blocked/...
  output-contract/SKILL.md# fenced block lhtm-update + parse rules
```

Each SKILL.md frontmatter:

```yaml
---
name: <slug>          # e.g. lhtm-core, planner, executor
description: <one-line purpose, used by skill clients to decide relevance>
---
```

Body = the existing `skills/<name>.md` content, ASCII-clean, with cross-references
between skills made explicit (e.g. `planner` imports `lhtm-core` rules, `executor`
emits `output-contract` blocks). Follows the same pattern plugin skills use.

### 4.2 ASCII hygiene (repo-wide)

- Replace the 5 corrupted `U+FFFD` (replacement char) bytes in `skills/planner.md`,
  `skills/recovery.md`, `skills/verifier.md` with the correct ASCII text.
- Replace all non-ASCII glyphs (U+2192 `->`, em-dashes, smart quotes, etc.) in
  `docs/`, `skills/`, `policies/`, `examples/`, and top-level `*.md` with ASCII
  equivalents (`->`, `--`, straight quotes).
- Bilingual README content is KEPT (files are UTF-8, safe; only the Windows cp1252
  CONSOLE is the problem, and that is an engine-output concern, not file content).

### 4.3 Release documentation (6 files)

| File | Content |
|---|---|
| `README.md` | exists bilingual; update roadmap (P8+P9 done) + install/skills.sh section |
| `QUICKSTART.md` | 3 paths: run engine demo; `npx skills add owner/repo`; use in Antigravity / Claude Code / Codex |
| `ARCHITECTURE.md` | LLM proposes -> engine validates -> evidence decides; component map; JSON canonical state |
| `SECURITY.md` | default supervised; action_gate; redactor; mode escalation; switch_to_safe_mode never raises |
| `LIMITATIONS.md` | engine is local Python (skill clients cannot run it); no LLM baseline A-E; FULL_AUTO needs trust |
| `EVALUATION.md` | P8 results: 8 fixtures, 5 metrics vs task.md targets, how to rerun |

All ASCII-only.

### 4.4 Packaging + CI + example

- **`pyproject.toml`**: `[project]` name/version/requires-python>=3.13/description;
  `[project.optional-dependencies] dev = [PyYAML, ruff]`; `[tool.ruff]`; `[tool.pytest]`
  (so `pytest` also runs the stdlib unittest suite). NO `[project.scripts]`.
- **`LICENSE`**: MIT.
- **`.github/workflows/`**:
  - `test.yml` - ubuntu, python 3.13, `pip install pyyaml`, `python -m unittest discover -s tests`.
  - `lint.yml` - `pip install ruff`, `ruff check engine eval scripts`.
  - `eval.yml` - `pip install pyyaml`, `python -m eval`, assert exit 0 + `eval/report.md`
    exists, upload report artifact.
- **`example/`**: `run_supervised_demo.py` (copy of `scripts/run_supervised.py`,
  runs from the example dir) + `README.md`.

### 4.5 Final repo layout

```
engine/lhtm/          # 20 engine modules
eval/                 # P8 harness + 8 fixtures
skills/               # 6 SKILL.md (skills.sh format)
policies/ examples/   # existing
scripts/              # demo_tahap1, run_supervised
example/              # run_supervised_demo.py + README
docs/superpowers/     # specs + plans P0-P9
README QUICKSTART ARCHITECTURE SECURITY LIMITATIONS EVALUATION
pyproject.toml LICENSE .github/workflows/
```

## 5. Testing

- `python -m unittest discover -s tests -p "test_*.py"` -> 236 pass (unchanged).
- `python -m eval` -> 8 cases, passed=True, exit 0 (unchanged).
- New verification: a small script asserts every `skills/**/SKILL.md` has valid YAML
  frontmatter with `name` + `description`; asserts repo-wide ASCII (no glyph > 127)
  in docs/skills/policies/examples and top-level md.
- CI workflows are written and syntactically valid (YAML parses) but not executed
  until the repo is public (Actions needs public/remote; defer).

## 6. Success criteria

- 236 tests green; `python -m eval` passed=True.
- 6 SKILL.md with valid frontmatter; flat `skills/*.md` gone.
- ASCII-clean docs/skills/policies/examples; corrupted chars fixed.
- pyproject.toml + LICENSE + 3 CI workflows + example/ present and valid.
- task.md P9 checkboxes ticked (repo remains private).

---

## Spec Self-Review

- **Placeholder scan:** every deliverable named with contract; no TBD.
- **Internal consistency:** skill names match existing files; docs list matches
  task.md P9; CI workflows match the test commands actually used (unittest, not pytest).
- **Scope check:** single "release packaging" subsystem; one plan. Fits.
- **Ambiguity check:** "stay private" resolved (artifacts prepared, publish later);
  "skills.sh conversion" resolved (6 sub-skills, skills/<name>/SKILL.md); "bilingual
  README kept" explicit; ASCII hygiene scoped to repo content, not file encoding.
