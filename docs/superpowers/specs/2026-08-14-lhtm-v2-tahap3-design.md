# LHTM v2 -- Tahap 3 (P4: Evidence Verification + P5: Safe Command gaps) Design

> **Agentic workers:** After approval, implementation proceeds via writing-plans -> subagent-driven-development.

**Date:** 2026-08-14
**Status:** Draft for user review

---

## 1. Goal

Buka celah terakhir di rantai deterministik: **`claimed_done` tidak bisa menjadi `verified_done` tanpa bukti terverifikasi.** Verifier Python deterministik mengecek evidence vs `definition_of_done` + `allowed_paths` + keberadaan file. Engine menyelesaikan transisi atomik saat update `claimed_done` diterima. Serta menutup sisa celah P5 (timeout terkonfigurasi, cap retry, error hint).

Prinsip inti (tidak berubah):

```
LLM proposes. Engine validates. Evidence decides.
JSON canonical state. Markdown hanya generated view.
Eksekusi terikat active_task_id.
Guardrail deterministik, bukan hanya prompt.
```

## 2. Non-Goals (defer ke tahap berikutnya)

- **LLM verifier second pass** (P7/P9): verifier Tahap 3 deterministik murni. Interface pluggable tidak dibuat -- YAGNI sampai ada binding LLM nyata.
- **Status `needs_more_work`** (ke-9): kegagalan verifikasi memakai `failed` yang sudah ada (engine sudah membersihkan `active_task_id`).
- **Recovery phase machine** (P6), **redactor** (P7), **runbook** (P7), **context_budget** (P7), **real-LLM binding** (P9).

Alasan defer: Tahap 3 fokus pada verifikasi deterministik yang benar-benar bisa diuji + menutup celah safe-command yang tersisa. Lapisan LLM dan recovery adalah berikutnya.

## 3. Architecture

```
Engine Tahap 1+2 (state_store, schema_validator, parser, markdown_view, constants,
                  task_scheduler, context_builder, action_gate, safe_executor,
                  prompt_loader, audit, config)
        │
        v
evidence_verifier.py   -- [BARU] verifikasi deterministik evidence vs DoD/allowed_paths/file
engine.process_update  -- pada claimed_done: verifier -> verified_done (pass) | failed+feedback (fail)
safe_executor.py       -- [HARDEN] timeout konfig, retry cap, error hint
```

Alur per-turn (ekstensi Tahap 2 sec.3):

```
1. scheduler.pick_next(state) -> task
2. engine.activate_task(task_id)  (gate: ready, one-active, max_attempts)
3. context = context_builder.build(state, task, config, errors=feedback_loop)
4. [driver] LLM -> respon (fixture di Tahap 3)
5. parser.extract_updates(respon) -> update
6. schema_validator.validate_update(update)  (reject engine-owned, butuh evidence utk claimed_done)
7. action_gate.check(proposed_actions) -> allowed/rejected
8. safe_executor.execute(action, gate_result, task) -> hasil
9. engine.process_update(update)
     ├─ claimed_done -> EvidenceVerifier.verify(state, task, config)
     │     ├─ pass -> status = verified_done (engine-owned), clear active, log task.verified
     │     └─ fail -> status = failed, clear active, task["feedback"] = reason, log task.verify_failed
     └─ lainnya -> perilaku Tahap 1/2 (tidak berubah)
10. audit.log_step(...)
11. markdown_view.render_tracker(state)
12. loop / blocked / done
```

## 4. New Component Contract

### 4.1 `evidence_verifier.py`

```python
class EvidenceVerifier:
    def verify(self, state: dict, task: dict, config: dict) -> dict
    # -> {"verdict": "pass"|"fail", "feedback": str|None, "checks": [str]}
```

Checks deterministik, berurutan, masing-masing masuk daftar `checks`:

1. **Evidence present**: `task["evidence"]` non-kosong (schema sudah mewajibkan untuk `claimed_done`).
2. **Paths in allowed_paths**: setiap `path` di evidence (dan `artifacts`) ada di dalam salah satu `task["allowed_paths"]` -- pakai semantik `action_gate._path_allowed` (sama/prefix/glob).
3. **Files exist**: setiap path evidence bertipe `file_created` (atau terdaftar di artifacts) benar-benar ada di disk (CWD-relative, konsisten dengan executor).
4. **DoD coverage**: setiap item `definition_of_done` ter-cover oleh >= 1 evidence (substring match deterministik pada note/path/type).
5. **Test evidence**: jika ada item DoD yang menyebut `test`/`pass`/`lint`, harus ada evidence `type == "test_pass"`.

Semua lolos -> `{"verdict": "pass"}`. Ada gagal -> `{"verdict": "fail", "feedback": "...check mana yang gagal + item"} `. Tanpa LLM, tanpa panggilan eksternal.

Aturan feedback: `feedback` menyebut check yang gagal dan item spesifik (mis. `file missing: src/cli.py`), agar driver/executor bisa retry dengan hint.

### 4.2 Engine hook (`engine.py`)

`process_update(update)` saat `update["status"] == "claimed_done"`:

- Setelah menerapkan evidence/artifacts, jalankan `EvidenceVerifier().verify(state, task, config)`.
- **Pass** -> transisi engine-owned `claimed_done -> verified_done`, `active_task_id = None`, log `task.verified`.
- **Fail** -> `status = "failed"`, `active_task_id = None`, `task["feedback"] = verifier.feedback`, log `task.verify_failed`.
- Return diperluas: `{"accepted": bool, "errors": [...], "verdict": str|None, "feedback": str|None}`.

`verified_done` tetap **engine-owned** -- `schema_validator.validate_update` sudah menolak LLM men-set-nya (Tahap 1). `_save()` sudah memvalidasi state sebelum write.

### 4.3 P5 hardening (`safe_executor.py`)

Tidak ada modul baru; hanya menutup celah yang tersisa:

1. **Timeout konfigurasi**: `_run_command` membaca `limits.max_cmd_timeout` (key baru, default 60) menggantikan hardcode 60.
2. **Retry cap**: config `limits.max_repair_attempts` (default 2). Verifier-fail menaikkan beban menuju cap via `attempts`; `activate_task` sudah menolak saat `attempts >= max_attempts`. Eksekutor tidak perlu logika tambahan -- cap sudah ditegakkan engine.
3. **Error hint**: `_run_command` failure mengembalikan `error = "command exited with code N"` + output terpotong di `result` (sudah ada). Driver/context_builder menyuntikkan feedback ke turn berikutnya via param `errors` (sudah ada).

## 5. Trust Boundary

Tetap: **LLM output = untrusted.** Verifier adalah lapisan deterministik ke-4 setelah parser, validator, gate. Verifier TIDAK percaya klaim LLM -- ia memeriksa realita (file ada? path diizinkan? DoD ter-cover?).

Pola yang ditolak engine (bukan hanya prompt):
- Klaim done tanpa evidence -> ditolak schema (Tahap 1).
- Evidence path di luar `allowed_paths` -> verifier fail.
- Evidence file tidak ada di disk -> verifier fail.
- DoD tidak ter-cover evidence -> verifier fail.
- `verified_done` dari LLM -> ditolak schema (engine-owned).

## 6. Error Handling

- Verifier fail -> `status = failed`, `active_task_id` cleared (perilaku engine lama), feedback di `task["feedback"]`. Tidak hang, loop bisa lanjut ke task lain.
- Retry: `failed -> ready` legal; driver boleh promote ulang; `activate_task` menolak saat `attempts >= max_attempts` (cap).
- Update invalid -> ditolak `process_update` seperti Tahap 1/2 (tidak berubah).

## 7. Testing

- `test_evidence_verifier.py`: pass pada evidence lengkap; fail pada file missing, path out-of-scope, DoD uncovered, test_pass missing, evidence kosong.
- `test_engine.py` (tambah): claimed_done + evidence baik -> `verified_done` + active cleared; evidence buruk -> `failed` + feedback; log event `task.verified`/`task.verify_failed`.
- `scripts/run_supervised.py` (update): T01 claim dengan file nyata + evidence `test_pass` -> `verified_done` (tanpa hack manual); satu task dengan evidence buruk -> `failed` + feedback ditampilkan.
- Seluruh suite Tahap 1+2 (148) tetap hijau.

Target: suite Tahap 3 hijau (148 lama + verifier + engine additions).

## 8. Dependencies

- Tidak ada dep baru. stdlib: os, pathlib, re, unittest.

## 9. Deliverables / Exit Criteria

- `engine/lhtm/evidence_verifier.py` (baru)
- `engine/lhtm/engine.py` (hook claimed_done -> verifier)
- `engine/lhtm/config.py` (key `limits.max_cmd_timeout`)
- `engine/lhtm/safe_executor.py` (baca `max_cmd_timeout`)
- `tests/test_evidence_verifier.py` (baru), `tests/test_engine.py` (tambah)
- `scripts/run_supervised.py` (update: verifier nyata, tanpa hack manual verified_done)
- 148 test lama + test baru hijau
- Tidak ada `verified_done` tanpa bukti terverifikasi

**Exit:** klaim done tanpa bukti -> `failed` + feedback; klaim done dengan bukti sah -> `verified_done` otomatis; retry terbatas; suite hijau.
