# LHTM v2 — Sprint Plan

Pecahan dari `Implementation_plan.md` menjadi sprint bertahap. Urutan **P0 → P9** mengikuti milestone M0–M7 dan 4 tahap rollout yang aman.

Prinsip yang harus dipegang semua sprint:

```
LLM proposes. Engine validates. Evidence decides.
JSON canonical state. Markdown hanya generated view.
Eksekusi terikat active_task_id.
Guardrail deterministik, bukan hanya prompt.
```

---

## P0 — Specification Freeze (Milestone 0)

Tujuan: bekukan semua skema & aturan sebelum menulis kode. Sumber: Phase 1 + Phase 4 (daftar komponen).

- [ ] Definisikan `state.json` schema (Phase 4.2): `schema_version`, `run_id`, `goal` (frozen+hash), `phase`, `mode`, `active_task_id`, `policy`.
- [ ] Definisikan **task model** (Phase 4.3): `id`, `title`, `objective`, `status`, `depends_on`, `risk_level`, `allowed_paths`, `allowed_commands`, `definition_of_done`, `artifacts`, `evidence`, `attempts`, `max_attempts`.
- [ ] Tetapkan daftar **status task** (8): `pending/ready/active/blocked/claimed_done/verified_done/failed/skipped`.
- [ ] Tetapkan daftar **fase** (12): `DRAFT..COMPLETED/ABORTED` (Phase 4.4).
- [ ] Tulis **tabel transisi fase legal + ilegal** (Phase 4.4).
- [ ] Definisikan **event log** schema + daftar event penting (Phase 4.5).
- [ ] Definisikan **plan schema** (Phase 5.3) dan **update schema** (Phase 6.3).
- [ ] Definisikan **security policy** default (`config.yaml`, Phase 9.1).
- [ ] Definisikan **mode eksekusi** (4): `DRY_RUN/SUPERVISED/AUTO_SAFE/FULL_AUTO`.
- [ ] Definisikan **runbook schema + approval tier** (Phase 10.1, 10.3).

Exit: semua schema & aturan terdokumentasi dan disetujui.

---

## P1 — Stateful Planning (Milestone 1)

Tujuan: goal → plan JSON valid → state tersimpan → tracker generated. Belum ada eksekusi file/command. Sumber: Phase 1, Phase 5.1, 8.1.

- [ ] Buat struktur direktori `.lhtm/` (Phase 4.1): `state.json`, `events.jsonl`, `plans/`, `artifacts/`, `logs/`, `snapshots/`, `config.yaml`.
- [ ] Implement `state_store.py`: `load_state/save_state` atomic + lock file (Phase 7.2).
- [ ] Implement backup + `create_snapshot/restore_snapshot` (Phase 7.2).
- [ ] Implement `schema_validator.py` untuk plan & state (Phase 7.3).
- [ ] Implement goal hash check (anti goal-change diam-diam).
- [ ] Implement `markdown_view.py`: generate `progress_tracker.md` dari state (Phase 4.6).
- [ ] Buat skill `planner.md` (Phase 5.3): output JSON `lhtm.plan/v1`.
- [ ] Buat flow planning (Phase 8.1): validasi → `open_questions` → simpan state → user approve → `READY`.

Exit: plan valid 100% pada fixture, state tidak korup, tracker sinkron.

---

## P2 — Skill Pack + Output Contract (Phase 2 & 3)

Tujuan: prompt yang disiplin + format output yang wajib diparse. Sumber: Phase 2, Phase 3.

- [ ] Buat `lhtm_core.md` (10 aturan non-negotiable, Phase 5.2).
- [ ] Buat `executor.md` (Phase 5.4).
- [ ] Buat `verifier.md` (Phase 5.6).
- [ ] Buat `recovery.md` (Phase 5.7).
- [ ] Buat `output_contract.md` (Phase 6.1): fenced block `lhtm-update`.
- [ ] Buat `examples/`: `valid_update.json`, `invalid_update.json`, `plan.json`, `task_card.md`.
- [ ] Buat `policies/`: `security.md`, `action_allowlist.md`, `completion_rules.md`.
- [ ] Batasi status yang boleh dikirim LLM (5) vs yang dilarang (`verified_done`, `completed`, dst) — Phase 6.2.
- [ ] Implement parser blok `lhtm-update` + JSON repair loop (max 2 repair) — Phase 6.3.
- [ ] Implement task card injection (`ACTIVE_TASK`, `ALLOWED_PATHS`, `DEFINITION_OF_DONE`) — Phase 5.5.

Exit: output LLM bisa diparse deterministik; invalid → repair prompt otomatis.

---

## P3 — Supervised Executor (Milestone 2)

Tujuan: satu task aktif dieksekusi, aksi diawasi user. Sumber: Phase 4 (gate/executor), Phase 5.2, Phase 8.2.

- [ ] Implement `task_scheduler.py`: pilih `ready` task, tolak dependensi belum selesai / high-risk tanpa approval / over attempt (Phase 7.4).
- [ ] Implement `context_builder.py`: inject goal + task card + policy + errors + file relevan (Phase 7.5, Phase 8).
- [ ] Implement `action_gate.py` (komponen keamanan inti, Phase 7.6): cek active_task, allowed_paths, allowlist, secret, file sensitif, command destruktif.
- [ ] Implement `safe_executor.py` mode `SUPERVISED` default (Phase 7.7).
- [ ] Implement `prompt_loader.py`.
- [ ] Implement execution loop per-turn (Phase 8.2, 16 langkah).
- [ ] LLM boleh usulkan `write_file`, user approve/reject; diff ditampilkan.
- [ ] Implement `audit.py`: append event ke `events.jsonl` (Phase 7.10).

Exit: invalid update ditolak, repair loop bekerja, out-of-scope write diblokir.

---

## P4 — Evidence Verification (Milestone 3)

Tujuan: `claimed_done` tidak bisa jadi `verified_done` tanpa bukti. Sumber: Phase 7.8, Phase 8.3.

- [ ] Implement `evidence_verifier.py`: cek file exists, allowed_paths, test/lint, `definition_of_done` (Phase 7.8).
- [ ] Terapkan urutan: `Python checks first → LLM verifier second` (Phase 5.6).
- [ ] Implement flow verifikasi task (Phase 8.3): gagal → `failed/needs_more_work` + feedback ke executor.
- [ ] Terapkan aturan: klaim done tanpa evidence → `needs_more_work` (kasus 3, Phase 17).
- [ ] Integrasikan verifier skill sebagai second pass (bisa model lebih kuat / deterministik).

Exit: false completion turun signifikan; tidak ada `verified_done` tanpa bukti.

---

## P5 — Safe Command Execution (Milestone 4)

Tujuan: jalankan command allowlist, aman dan terbatas. Sumber: Phase 7.7, Phase 8.4, Phase 9.2.

- [ ] Implement runner command allowlist (structured: `tool` + `args`, bukan raw shell) — Phase 9.2.
- [ ] Tangkap stdout/stderr + ringkas output sebelum dikirim ke model (Phase 8.4, Phase 11.4).
- [ ] Kirim error summary balik ke executor dengan hint (kasus 4, Phase 17).
- [ ] Batasi retry (`max_attempts`, `max_repair_attempts`) — Phase 8.4.
- [ ] Blokir command berbahaya: `rm -rf`, `sudo`, `curl|bash`, `chmod 777`, force push, drop db, dst (Phase 7.7).

Exit: command berbahaya tak bisa jalan, output besar tidak merusak context, failure loop berhenti.

---

## P6 — Recovery & Robustness (Milestone 5)

Tujuan: sistem tidak hang saat error. Sumber: Phase 5.7, Phase 8.4.

- [ ] Implement `recovery.py`: aksi `retry_with_hint/decompose_task/request_user_input/mark_blocked/rollback_proposal/switch_to_safe_mode`.
- [ ] Recovery dari output invalid (repair loop → `BLOCKED`).
- [ ] Recovery dari state korup (snapshot/restore).
- [ ] Recovery dari command failure (increase attempt → failed → `RECOVERY`/`WAITING_USER`).
- [ ] Implement blocker escalation ke user.

Exit: tidak hang saat error, audit log lengkap, state bisa dipulihkan.

---

## P7 — Security & Context Hardening (Phase 6, 7, 8)

Tujuan: tahan penyalahgunaan + hemat token. Sumber: Phase 6, 7, 8.

- [ ] Implement `redactor.py`: redact secret (`.env`, `*.pem`, `api_key`, `password`, dst) — Phase 7.9.
- [ ] Terapkan file access blocklist (`.env`, kredensial, `.aws/`, `.kube/`, dst) — Phase 9.3.
- [ ] Terapkan prompt injection defense (content eksternal = untrusted) + penolakan di engine — Phase 9.4.
- [ ] Implement structured runbook runner: idempotent, backup, timeout, dry-run, stop-on-failure — Phase 10.2.
- [ ] Implement context hierarchy + token budget (`context_budget`) — Phase 11.1, 11.4.
- [ ] Buat `project_facts.md` + code context selection (`allowed_paths`, file berubah, file gagal test) — Phase 11.2, 11.3.

Exit: secret tidak bocor, aksi luar scope ditolak engine (bukan cuma prompt), context hemat token.

---

## P8 — Evaluation Harness (Milestone 6)

Tujuan: buktikan secara kuantitatif. Sumber: Phase 9 (12), Phase 18.

- [ ] Unit test: `state_store`, `schema_validator`, parser, `task_scheduler`, `action_gate`, `redactor`, `markdown_view` (Phase 12.1).
- [ ] Integration test: planning loop, execution loop, repair loop, runbook runner, recovery flow.
- [ ] Adversarial suite (10 kasus, Phase 12.1): prompt injection, invalid JSON, output terpotong, klaim done tanpa evidence, tulis `.env`, `rm -rf`, tracker korup, command gagal, goal berubah, dependensi siklik.
- [ ] Scenario benchmark (8 kategori, Phase 12.1) — bukan cuma 2 skenario.
- [ ] Baseline comparison A–E (Phase 12.2), 3–5 run/scenario, temperature rendah.
- [ ] Metrics collector: kepatuhan, penyelesaian, kualitas, keamanan, efisiensi (Phase 12.3).
- [ ] Report generator (Phase 18).
- [ ] Target sukses minimal (Phase 12.4): `schema_valid_rate > 98%`, `false_completion < 5%`, `out_of_scope = 0`, `secret_leak = 0`, `test_pass > 70%`.

Exit: laporan evaluasi otomatis, metrik utama terukur.

---

## P9 — Public Release (Milestone 7)

Tujuan: rilis aman dengan default supervised. Sumber: Phase 10 (13), Phase 19.

- [ ] Susun repositori final (`gemini-flash-lhtm/`) sesuai Phase 13.
- [ ] `README.md`, `QUICKSTART.md`, `ARCHITECTURE.md`, `SECURITY.md`, `LIMITATIONS.md`, `EVALUATION.md`.
- [ ] Example project + `run_supervised_demo.py`.
- [ ] CI workflows: `test.yml`, `lint.yml`, `eval.yml`.
- [ ] `pyproject.toml`, `LICENSE`.
- [ ] Pastikan default mode `supervised`, secure defaults, tanpa critical security issue.

Exit: CI hijau, dokumentasi limitasi jelas, default supervised.

---

## Urutan Rollout Aman (referensi 4 tahap)

| Tahap | Isi | Sprint terkait |
|---|---|---|
| 1. Skill-only mode | planning + decomposition + tracking, human eksekusi manual | P0–P2 |
| 2. Supervised file edits | LLM usulkan diff → user approve → evidence dicatat | P3 |
| 3. Safe test runner | engine jalankan test/lint, ringkas, retry terbatas | P4–P5 |
| 4. Limited auto-run | low-risk auto, approval untuk write penting, audit + snapshot | P6–P7 |

---

## Catatan

- Sprint P0–P2 sudah memberi nilai tanpa eksekusi otomatis (aman).
- `action_gate` (P3) adalah komponen keamanan paling kritis — prioritaskan benar-benar deterministik.
- Semua target angka di P8 adalah target, bukan janji; sesuaikan saat benchmark nyata.
