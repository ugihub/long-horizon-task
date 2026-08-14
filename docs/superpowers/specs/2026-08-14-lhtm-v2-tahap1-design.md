# LHTM v2 — Tahap 1 (P0–P2) Design Spec

Tanggal: 2026-08-14
Status: Draft
Cakupan: Sprint P0 (Spec Freeze), P1 (Stateful Planning), P2 (Skill Pack + Output Contract). Ini = Rollout Tahap 1: **Skill-only mode** — planning, decomposition, tracking; eksekusi tetap manual oleh human. Belum ada eksekusi file/command oleh engine.

## 1. Prinsip Sistem

```
LLM proposes. Engine validates. Evidence decides.
JSON canonical state. Markdown hanya generated view.
Eksekusi terikat active_task_id.
Guardrail deterministik, bukan hanya prompt.
```

- **JSON adalah sumber kebenaran.** `state.json` + `events.jsonl` + `plans/*.json` canonical. Semua `.md` (tracker, task card, skill docs) = generated/static view, bukan state.
- **Deterministik**: parser, validator, scheduler, gate semuanya logika Python + stdlib, zero-LLM.
- **Tahap 1 tidak mengeksekusi apapun.** P0–P2 hanya: schema, state store, validator, tracker generator, skill pack, parser output contract, repair loop.

## 2. Struktur Direktori

```
long-horizon-task/
├── docs/superpowers/specs/          # design docs
├── engine/                          # Python engine (stdlib only)
│   ├── lhtm/
│   │   ├── __init__.py
│   │   ├── state_store.py           # atomic load/save + lock + snapshot
│   │   ├── schema_validator.py      # state & plan validation
│   │   ├── parser.py                # lhtm-update fenced block parser + repair
│   │   ├── markdown_view.py         # progress_tracker.md generator
│   │   ├── constants.py             # fase, status, mode, policy defaults
│   │   └── goal_hash.py             # goal frozen + sha256 check
│   └── test_*.py                    # assert-based, stdlib unittest
├── skills/                          # skill pack (Prompt content)
│   ├── lhtm_core.md                 # 10 aturan non-negotiable
│   ├── planner.md                   # plan JSON output contract
│   ├── executor.md                  # per-turn execution skill
│   ├── verifier.md
│   ├── recovery.md
│   └── output_contract.md           # lhtm-update fenced block spec
├── policies/
│   ├── security.md
│   ├── action_allowlist.md
│   └── completion_rules.md
├── examples/
│   ├── valid_update.json
│   ├── invalid_update.json
│   ├── plan.json
│   └── task_card.md
├── .lhtm/                           # generated at runtime, gitignored
└── task.md / Implementation_plan.md
```

## 3. Schema Canonical

### 3.1 `state.json` (Phase 4.2)
```json
{
  "schema_version": "1.0",
  "run_id": "uuid",
  "goal": {"text": "...", "hash": "sha256", "frozen_at": "ISO8601"},
  "phase": "DRAFT",
  "mode": "DRY_RUN",
  "active_task_id": null,
  "policy": {"security_level": "default", "max_attempts": 3, "max_repair_attempts": 2},
  "tasks": [Task],
  "current_step": 0
}
```
- `goal.hash` = sha256 dari text goal. Setiap load/save divalidasi — perubahan goal = korupsi.

### 3.2 Task model (Phase 4.3)
```json
{
  "id": "T01",
  "title": "...",
  "objective": "...",
  "status": "pending",
  "depends_on": [],
  "risk_level": "low|medium|high",
  "allowed_paths": [],
  "allowed_commands": [],
  "definition_of_done": ["..."],
  "artifacts": [],
  "evidence": [],
  "attempts": 0,
  "max_attempts": 3
}
```

### 3.3 Status task (8, tetap)
`pending / ready / active / blocked / claimed_done / verified_done / failed / skipped`

Transisi valid (engine-enforced):
```
pending  -> ready | skipped
ready    -> active | blocked | skipped
active   -> claimed_done | failed | blocked
blocked  -> pending | ready | failed
claimed_done -> verified_done | failed | active   (needs evidence)
verified_done -> (terminal)
failed   -> (terminal) | ready        (after manual reset w/ approval)
skipped  -> (terminal)
```
Ilegal (harus tolak): `pending->active`, `claimed_done->pending`, `verified_done->active`, dsb.

### 3.4 Fase (Phase 4.4)
12 fase (sumber: `Implementation_plan.md` §4.4): `DRAFT, PLANNING, PLAN_REVIEW, READY, EXECUTING, VERIFYING, BLOCKED, WAITING_USER, FAILED, RECOVERY, COMPLETED, ABORTED`.

Model transisi = **state machine dengan edge eksplisit**, bukan monotonic index (dari contoh legal di §4.4: `VERIFYING->READY`, `RECOVERY->READY` legal walau mundur). Tabel edge `PHASE_TRANSITIONS`:

```
DRAFT       -> PLANNING, PLAN_REVIEW
PLANNING    -> PLAN_REVIEW, READY, DRAFT
PLAN_REVIEW -> READY, PLANNING
READY       -> EXECUTING, COMPLETED, PLAN_REVIEW
EXECUTING   -> VERIFYING, BLOCKED
VERIFYING   -> READY, FAILED, EXECUTING
FAILED      -> RECOVERY
RECOVERY    -> READY, EXECUTING
BLOCKED     -> WAITING_USER, EXECUTING
WAITING_USER-> READY, PLANNING
COMPLETED   -> (terminal)
ABORTED     -> (terminal)
```

Aturan: target di `RECOVERY_PHASES` (`BLOCKED/WAITING_USER/FAILED/RECOVERY/ABORTED`) selalu legal dari fase mana pun. Source tanpa row eksplisit default = maju satu fase. `COMPLETED`/`ABORTED` terminal (tidak bisa keluar). Ilegal: `COMPLETED->EXECUTING`, `ABORTED->READY`, dst.

### 3.5 Event log `events.jsonl` (Phase 4.5)
Satu JSON per baris:
```json
{"ts":"ISO8601","event":"task.created","task_id":"T01","data":{...},"hash":"sha256-pprev"}
```
Event penting: `run.started, goal.frozen, plan.submitted, plan.approved, task.created, task.activated, task.claimed_done, task.verified_done, task.failed, repair.attempted, state.restored, goal.mismatch`.

### 3.6 Plan schema (Phase 5.3)
```json
{
  "schema_version": "1.0",
  "run_id": "...",
  "goal_hash": "...",
  "title": "...",
  "objective": "...",
  "tasks": [Task],
  "open_questions": ["..."],
  "metadata": {"model": "...", "generated_at": "...", "generator": "planner"},
  "approved": false
}
```
Validasi: semua task punya id unik, status `pending`, dependensi merujuk id yang ada, tidak ada dependensi siklik (topo check), `goal_hash` cocok.

### 3.7 Update schema (Phase 6.3) — output contract LLM
Fenced block `lhtm-update`:
````
```lhtm-update
{
  "task_id": "T01",
  "status": "claimed_done",
  "evidence": [{"type": "file_created", "path": "...", "note": "..."}],
  "artifacts": ["..."],
  "context": {"rationale": "...", "next_step": "..."}
}
```
````
Status yang BOLEH dikirim LLM (5): `pending, ready, active, blocked, claimed_done, failed`. DILARANG: `verified_done, completed, skipped` (engine yang memutuskan).

### 3.8 Mode eksekusi (Phase 9.1) — 4
`DRY_RUN / SUPERVISED / AUTO_SAFE / FULL_AUTO`. Default Tahap 1 = `DRY_RUN`.

### 3.9 Security policy default (`config.yaml`, Phase 9.1 — representasi skema P0)
Tahap 1 menyimpan representasi skema policy; enforcement penuh di P3 (`action_gate`) & P7 (`redactor`). Isi: `action_allowlist`, `path_blocklist`, `command_denylist`, `secret_patterns`, `max_attempts`.

## 4. Komponen Engine (Python stdlib)

### 4.1 `state_store.py`
- `load_state(path) -> dict` — parse + validate minimal (schema_version, run_id, goal.hash).
- `save_state(state)` — atomic: tulis `state.json.tmp`, fsync, rename. Mencegah state korup saat crash.
- Lock file: `state.json.lock` menandai akses eksklusif.
- `create_snapshot()` → salin ke `.lhtm/snapshots/state-<timestamp>.json`.
- `restore_snapshot(path)` → pulihkan + log event `state.restored`.

### 4.2 `schema_validator.py`
- `validate_state(state)` / `validate_plan(plan)` / `validate_update(update)`.
- Return list error. Strict: jalur `depends_on` ketemu, status legal, goal_hash cocok.
- Topo check anti-siklik untuk plan.

### 4.3 `goal_hash.py`
- `freeze_goal(text)` → simpan text + sha256.
- `check_goal(state)` → raise/mismatch kalau hash berubah.

### 4.4 `parser.py`
- `extract_updates(llm_output: str) -> list[dict]` — temukan fenced block `lhtm-update` (```lhtm-update ... ```).
- `repair_json(text)` — max 2 repair pass: fix trailing comma, unclosed quotes, brace balancing. Gagal → `{"errors": [...]}`.
- Deterministik, tanpa LLM.

### 4.5 `markdown_view.py`
- `render_tracker(state) -> str` — progress table dari tasks (status, dep, risk, attempts, evidence checklist), ringkasan fase/mode/goal.
- Ditulis ke `progress_tracker.md`. Murni derived — kalau dihapus bisa diregen dari state.

## 5. Skill Pack (P2)

### 5.1 `lhtm_core.md` — 10 aturan non-negotiable
1. JSON canonical; markdown hanya view. 2. Satu task aktif (`active_task_id`). 3. Status legal per aturan transisi. 4. `claimed_done` WAJIB sertakan evidence. 5. Dilarang ubah `verified_done`. 6. Keluar blok `lhtm-update` valid setiap giliran. 7. Hanya path di `allowed_paths`. 8. `definition_of_done` penentu selesai. 9. Propose, jangan eksekusi (Tahap 1). 10. Goal frozen — jangan ubah.

### 5.2 `planner.md` — plan output contract
Ouput plan JSON `lhtm.plan/v1`. Termasuk daftar `open_questions`.

### 5.3 `executor.md` — per-turn
Baca task card, lakukan langkah, keluar `lhtm-update`.

### 5.4 `verifier.md` — evidence terhadap `definition_of_done`.
### 5.5 `recovery.md` — retry_with_hint / decompose / request_user_input / mark_blocked.
### 5.6 `output_contract.md` — spek fenced block `lhtm-update` + daftar status boleh vs dilarang + JSON repair info.

## 6. Status LLM vs Engine
- LLM dapat kirim: `pending, ready, active, blocked, claimed_done, failed`.
- Engine OWN: `verified_done, completed, skipped`, plus semua transisi ilegal.
- `verified_done` hanya dihasilkan Verifier (P4) — di Tahap 1 tidak ada jalur menuju `verified_done`.

## 7. Contoh Quickstart (Tahap 1 alur)
1. User kasih goal → planner (LLM) hasilkan `plan.json` + `open_questions`.
2. Engine: validasi plan (goal hash, cycle, task schema) → simpan state.
3. `markdown_view` produce `progress_tracker.md`.
4. Pengguna review → approve → fase `READY`.
5. (Tahap 2+: executor per-turn, supervised.)

## 8. Error Handling
- Update invalid → `repair.json` max 2 pass → masih gagal → tolak + feedback ke LLM, event `repair.attempted`.
- State korup saat load → flag + restore dari snapshot terakhir.
- Goal mismatch → tolak semua update, log `goal.mismatch`.

## 9. Testing (per komponen, stdlib `unittest`)
- `state_store`: roundtrip, atomic rename, lock eksklusif, snapshot/restore.
- `schema_validator`: state valid, task ilegal status, dependensi siklik, goal hash mismatch.
- `parser`: blok valid, multiple blok, JSON rusak → repair success/fail.
- `markdown_view`: tracker sinkron dengan state setelah update.

## 10. Non-Goals Tahap 1
- Tidak eksekusi command / file write (P3).
- Tidak verifikasi evidence otomatis selain cek kehadiran field (P4).
- Tidak redaction secret aktif (P7).
- Tidak metrik eval (P8).
- `policies/` dan `config.yaml` = representasi skema saja, enforcement di P3+.