# LHTM v2 — Tahap 4 (P6: Recovery + P7: Security & Context Hardening) Design

> **Agentic workers:** After approval, implementation proceeds via writing-plans → subagent-driven-development.

**Date:** 2026-08-14
**Status:** Draft for user review

---

## 1. Goal

Tahap 4 = **Limited auto-run** (rollout table, baris 4): low-risk auto, approval untuk write penting, audit + snapshot. Menutup dua sprint sekaligus:

- **P6 (Recovery & Robustness):** sistem tidak hang saat error. Recovery ter-orchestrasi engine, reuses legal transitions, corrupt-state sudah ada (snapshot/restore).
- **P7 (Security & Context Hardening):** secret tidak bocor ke model, runbook aman, context hemat token, facts terpilih.

Prinsip inti (tidak berubah):

```
LLM proposes. Engine validates. Evidence decides.
JSON canonical state. Markdown hanya generated view.
Eksekusi terikat active_task_id.
Guardrail deterministik, bukan hanya prompt.
```

## 2. Non-Goals (defer)

- **LLM verifier second pass** (P9/P7 second pass) — verifier tetap deterministik murni (Tahap 3). Pluggable LLM binding masih YAGNI.
- **Redaction ke state persisten** — evidence/artifacts di state tetap RAW. Redaction hanya di layer model-facing (context, executor output, markdown render). Verifier butuh path asli.
- **Autonomous recovery module** — recovery adalah orchestrasi engine, bukan state machine otonom (keputusan user: engine-orchestrated).
- **Entropy secret scanning** — redactor pattern-only (keputusan user). Tanpa deteksi high-entropy.
- **Runbook + recovery integration** — runbook tidak auto-memicu phase transitions; stop-on-failure default, rollback runbook di-defer.
- **External tokenizer** — context_budget pakai char-count, bukan token estimator (keputusan user: budget + truncation).
- **Set_mode ke FULL_AUTO dari switch_to_safe_mode** — dilarang; safe mode hanya turun level.

## 3. Architecture

```
Engine Tahap 1-3 (state_store, schema_validator, parser, markdown_view, constants,
                  task_scheduler, context_builder, action_gate, safe_executor,
                  prompt_loader, audit, config, evidence_verifier)
        │
        ▼
recovery.py        — [BARU] RecoveryOrchestrator: engine.recover(task_id, action)
redactor.py        — [BARU] Redactor: redact(text) / redact_path(path) — model-facing only
runbook.py         — [BARU] RunbookRunner: validate/execute declarative runbook (operator-authored)
context_budget.py  — [BARU] ContextBudget: hierarchical build + per-section caps + truncation
project_facts.py   — [BARU] ProjectFacts: scan(allowed_paths) -> facts + excerpts
engine.py          — [HARDEN] recover(), set_mode(), decompose(), redactor hooks
action_gate.py     — [HARDEN] AUTO_SAFE risk-tiered approval
config.py          — [HARDEN] context_budget section + redact_patterns + facts caps
```

Mode baru dipakai penuh di Tahap 4: `DRY_RUN`/`SUPERVISED`/`AUTO_SAFE`/`FULL_AUTO` (sudah ada di constants sejak P0). AUTO_SAFE = limited auto-run.

## 4. Component Contracts

### 4.1 `recovery.py` — RecoveryOrchestrator

```python
class RecoveryOrchestrator:
    def validate_action(self, state, task_id, action, config) -> dict   # errors or ok
    def apply(self, state, task, action, config) -> dict                # mutates state
```

Engine wrapper: `engine.recover(task_id, action)` → validate → apply → save → log `recovery.action`.

Tabel aksi (setiap target adalah transisi legal yang SUDAH ada di `LEGAL_TASK_TRANSITIONS`):

| Action | Behavior | Task status -> | Phase -> |
|---|---|---|---|
| `retry_with_hint` | status=ready, `feedback`=hint; attempts TIDAK di-increment (hanya activate_task) | failed -> ready | READY |
| `request_user_input` | status=blocked, `feedback`=question | active/failed -> blocked | WAITING_USER |
| `mark_blocked` | status=blocked | active/failed -> blocked | WAITING_USER |
| `decompose_task` | butuh `proposed_subtasks`; engine `decompose(task_id, subtasks)` | active -> blocked (parent) | PLANNING |
| `rollback_proposal` | status=ready, feedback="rolled back", evidence+artifacts cleared | active -> ready | READY |
| `switch_to_safe_mode` | `set_mode(mode)`; valid: DRY_RUN/SUPERVISED/AUTO_SAFE (TIDAK FULL_AUTO) | (tak ubah status) | phase unchanged |

`validate_action` memakai `validator.validate_transition` untuk memastikan target legal dari status task saat ini; jika ilegal → tolak dengan error transisi.

**decompose:** parent status -> blocked; subtasks dibuat dengan `depends_on=[parent]`, `attempts=0`, `max_attempts` inherit. Scheduler sudah handle `depends_on`. Subtask selesai -> parent promote ke ready kembali (driver). 

**Command-failure / invalid-output recovery:** executor error summary sudah masuk `feedback`; parser `parse_error` sudah di-return. Driver tinggal memanggil `recover(..., "retry_with_hint")`. Tidak ada kode engine baru untuk path ini — orchestrator cukup butuh aksi legal.

**Corrupt-state:** reuse `store.restore_snapshot` / `create_snapshot` (sudah ada, no new code).

### 4.2 `redactor.py` — Redactor

```python
class Redactor:
    def __init__(self, patterns=None, placeholder="[REDACTED]")
    def redact(self, text: str) -> str
    def redact_path(self, path: str) -> str
```

- **Pattern-only** (keputusan user): plain-string, case-insensitive. Default: `.env`, `.env.*`, `api_key`, `apikey`, `password`, `passwd`, `secret`, `token`, `client_secret`, `access_token`, `*.pem`, `*.key`, `*.cert`, `*.crt`.
- **Redact value, bukan key:** `password: hunter2` -> `password: [REDACTED]`. Bentuk dipertahankan agar context tetap terbaca.
- **Inline secret:** nilai yang match pola secret panjang (mis. 40-hex, base64 run) -> placeholder. Tanpa entropy scan.
- **Hooks (model-facing SAJA):**
  1. `context_builder` / `context_budget` — redact assembled prompt sebelum return.
  2. `safe_executor._run_command` — redact stdout/stderr sebelum truncation.
  3. `markdown_view.render_tracker` — redact evidence notes / artifacts di render.
- **State + verifier tetap RAW** (keputusan user) — verifier butuh path asli untuk `Path.exists()`.
- **Config:** `security.redact_secrets` (sudah ada, default True) — jika False, redactor bypass. `security.redact_patterns` (custom, di-merge dgn defaults).

### 4.3 `runbook.py` — RunbookRunner

```python
class RunbookRunner:
    def validate(self, runbook: dict) -> list[str]
    def execute(self, runbook: dict, base_dir: str, config: dict, dry_run: bool = False) -> dict
    # -> {"ok": bool, "steps": [{"id","action","ok","error"}], "error": str|None}
```

Schema (declarative):

```json
{
  "runbook_version": 1,
  "title": "...", "description": "...",
  "steps": [
    {"id": "step1", "action": "run_command", "tool": "pytest", "args": ["-x"], "timeout": 120},
    {"id": "step2", "action": "write_file", "path": "src/x.py", "content": "...", "backup": true},
    {"id": "step3", "action": "assert", "path": "src/x.py", "contains": "def x"}
  ]
}
```

- `run_command` -> safe_executor path (list-form, timeout dari step atau `max_cmd_timeout`).
- `write_file` -> safe_executor `_write_file` (sudah backup overwrite ke `.bak`).
- `assert` -> cek file exists / contains; TANPA shell, rm, network.
- **Idempotent:** step keyed by `id`; state per-runbook di `.lhtm/runbooks/<name>.json`; step yang sudah selesai di-skip saat re-run.
- **Backup:** overwrite write backup `.bak` (sudah ada di executor).
- **Dry-run:** `dry_run=True` log planned steps, tidak menulis, tidak run command.
- **Stop-on-failure:** default True; step gagal -> return `ok=False` + error, step berikutnya tidak dijalankan.
- **Trust boundary:** runbook adalah **operator-authored artifact** di `.lhtm/runbooks/`. LLM TIDAK bisa menulis runbook; runbook TIDAK pernah dijalankan dari proposed_actions LLM.

### 4.4 `context_budget.py` — ContextBudget

```python
class ContextBudget:
    def __init__(self, config: dict)
    def build(self, state, task, config, errors=None, excerpts=None) -> str
```

- **Hierarchy** (proporsi `limits.max_context_tokens`): goal 5% | task card 25% | policy 15% | errors 10% | excerpts 40% | headroom 5%.
- **Truncation deterministic:** char-count (tanpa tokenizer). Cap per-section = `int(max_context_tokens * ratio)`. Excerpt per-file cap `max_excerpt_chars` (config baru, default 2000). Truncate dengan `... (truncated N chars)`.
- **Cascade drop:** jika assembled melebihi budget, drop excerpts -> errors -> policy sampai muat. TIDAK pernah melebihi budget.
- **Replaces `ContextBuilder.build`:** context_builder.py jadi thin wrapper delegasi ke ContextBudget (atau isinya dipindah). Hooks redactor di sini.

### 4.5 `project_facts.py` — ProjectFacts

```python
class ProjectFacts:
    def __init__(self, repo_root: str, config: dict)
    def scan(self, allowed_paths: list[str]) -> dict
    def render(self) -> str                       # -> project_facts.md text
```

- **Code context selection:** scan `allowed_paths`; return SUMMARY (top-N files by size / recent mtime / changed) bukan full contents. `summary` capped `max_facts_chars` (config baru, default 1500).
- **`project_facts.md`:** generated view -> `.lhtm/project_facts.md`, update on `engine._save` tick atau `engine.refresh_facts()`.
- **Excerpts:** untuk top files, baca `max_excerpt_chars` char pertama -> `context_budget.build(excerpts=...)`.
- **Read-only**, respect `allowed_paths` + `blocked_paths` (tidak baca file sensitif).

### 4.6 Mode escalation (`action_gate.py`)

| Mode | write/delete/run_command auto-approve |
|---|---|
| `DRY_RUN` | tidak ada eksekusi (executor reject / no-op) |
| `SUPERVISED` | tidak ada auto; semua butuh approval (status quo) |
| `AUTO_SAFE` | auto HANYA jika: path tidak blocked AND in allowed_paths AND risk_level=="low" AND overwrite target tidak sensitive; selain itu approval |
| `FULL_AUTO` | semua gate-approved auto-run |

- `engine.set_mode(mode)` validated thd `EXECUTION_MODES`.
- `switch_to_safe_mode` TIDAK bisa set ke FULL_AUTO.

## 5. Trust Boundary

Tetap: **LLM output = untrusted.** Tambahan di Tahap 4:
- Redactor melindungi model, bukan state — verifier tetap cek realita.
- Runbook operator-authored; LLM tidak bisa author runbook.
- Recovery aksi divalidasi engine (target transisi legal), LLM tidak bisa force status ilegal via recover.
- AUTO_SAFE masih deterministik: auto-approve hanya pada kriteria nyata (path/risk/overwrite), bukan tebakan LLM.

## 6. Error Handling

- Recovery action ilegal -> `recover` return `{"ok": False, "error": ...}`, state tak berubah.
- Command failure -> executor `error` + feedback (existing); driver recover `retry_with_hint`.
- Runbook step gagal -> stop-on-failure, return error; idempotency state tetap tersimpan (step yang sukses tidak diulang).
- Redactor: pattern yang tak match = no-op; input kosong = output kosong. Tidak raise.
- Context budget: section terlalu besar -> truncate/drop, tidak pernah melebihi budget.

## 7. Testing (per module, TDD)

- **recovery.py:** tiap aksi (legal + ilegal), attempts tidak di-increment pada retry, decompose bikin subtasks, switch_to_safe_mode tolak FULL_AUTO, state tidak berubah saat aksi tolak.
- **redactor.py:** redact value bukan key, `.env` path, inline token, disabled flag bypass, custom pattern, empty input.
- **runbook.py:** validate schema (missing id, bad action), run_command pass/fail, write_file + backup, assert contains, idempotency skip re-run, dry-run writes nothing, stop-on-failure.
- **context_budget.py:** budget cap terhormat, excerpt truncation, cascade drop, empty errors, missing excerpts.
- **project_facts.py:** respect allowed_paths, exclude blocked_paths, summary capped, empty dir.
- **action_gate AUTO_SAFE:** low-risk low-risk auto, high-risk butuh approval, sensitive-overwrite butuh approval.
- **engine:** `recover()` wrapper, `set_mode()` validation, `decompose()` subtasks, redactor hook di context.

Suite Tahap 1-3 (160) tetap hijau.

## 8. Dependencies

- Tidak ada dep baru. stdlib: re, os, pathlib, json, datetime, shutil, fnmatch.

## 9. Deliverables / Exit Criteria

- `engine/lhtm/recovery.py` (baru), `redactor.py` (baru), `runbook.py` (baru), `context_budget.py` (baru), `project_facts.py` (baru)
- `engine/lhtm/engine.py` (recover/set_mode/decompose/redactor hooks), `action_gate.py` (AUTO_SAFE), `config.py` (context_budget, redact_patterns, facts caps)
- `.lhtm/runbooks/` + `.lhtm/project_facts.md` generated views
- Suite Tahap 1-3 (160) + test baru hijau
- Secret tidak bocor ke model-facing output; runbook aman & idempotent; context tidak pernah over budget; AUTO_SAFE auto-hanya low-risk

**Exit:** tidak hang saat error (recovery engine-orchestrated), secret ter-redact di model layer, runbook deterministic, context hemat token, limited auto-run berjalan sesuai risk-tier.
