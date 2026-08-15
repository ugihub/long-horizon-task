# LHTM v2

**L**ong **H**orizon **T**ask **M**anager - a deterministic, engine-driven framework for
executing long-running agentic tasks safely and verifiably.

**LHTM v2** - kerangka kerja deterministik yang dijalankan oleh engine untuk mengeksekusi
tugas agen jangka panjang secara aman dan terverifikasi.

> **English** | [Bahasa Indonesia](#bahasa-indonesia)

---

## English

### What is LHTM?

LHTM turns "ask an agent to do a big multi-step task" into a structured, auditable,
safe process. Instead of trusting the LLM to behave, LHTM splits the work between an
**LLM that proposes** and a **deterministic engine that validates and decides**.

```
LLM proposes. Engine validates. Evidence decides.
JSON canonical state. Markdown is only a generated view.
Execution is bound to active_task_id.
Deterministic guardrails, not just prompts.
```

The engine never takes the model's word for anything: every state transition, file
write, and command must pass deterministic checks, and no task becomes `verified_done`
without verifiable evidence.

### Core ideas

- **LLM proposes, engine validates** - the model submits structured updates; the
  engine checks schema, legal transitions, allowed paths, allowlists, and destructive
  patterns before anything is applied.
- **Evidence decides** - `claimed_done` becomes `verified_done` only when the evidence
  verifier confirms it (file exists, in allowed paths, definition of done met).
- **JSON is the source of truth** - state lives in canonical JSON
  (`.lhtm/state.json`); the Markdown tracker is a generated view of it.
- **One active task** - execution is bound to `active_task_id`; the engine refuses
  out-of-order updates.
- **Deterministic guardrails** - security is enforced in code (`action_gate`,
  `safe_executor`, `redactor`), never left to a prompt.
- **4 execution modes** - `DRY_RUN`, `SUPERVISED`, `AUTO_SAFE`, `FULL_AUTO`.
  Default is `supervised`. `AUTO_SAFE` auto-approves only low-risk, non-sensitive
  actions; `switch_to_safe_mode` can lower a mode but can never raise to `FULL_AUTO`.

### Feature highlights

- **Stateful planning** - goal hashing, plan validation, 8 task statuses
  (`pending/ready/active/blocked/claimed_done/verified_done/failed/skipped`),
  legal transition table.
- **Action gate** - blocks out-of-scope writes, sensitive files (`.env`, `*.pem`,
  credentials), destructive commands (`rm -rf`, `sudo`, `curl|bash`, force push),
  and unapproved commands.
- **Safe executor** - structured `tool + args` (no raw shell by default), backups on
  overwrite, output truncation, per-command timeout, dry-run support.
- **Evidence verification** - `claimed_done` -> `verified_done` only after
  deterministic verification; failures return `failed` + feedback.
- **Recovery** (`P6`) - engine-orchestrated `retry_with_hint`, `request_user_input`,
  `mark_blocked`, `decompose_task`, `rollback_proposal`, `switch_to_safe_mode`; every
  target is a legally allowed transition.
- **Security & context hardening** (`P7`) - secret redaction (model-facing only),
  runbook runner (operator-authored, idempotent), budgeted context assembly,
  `project_facts` repo scan.

### Repository layout

```
engine/lhtm/            Deterministic engine (stdlib + PyYAML)
  engine.py             LhtmEngine facade (goal, plan, activate, recover, facts)
  state_store.py        Atomic state read/write + snapshots
  schema_validator.py   State / plan / update / transition validation
  task_scheduler.py     Picks the next runnable task
  action_gate.py        Security core: path/command/approval checks
  safe_executor.py      Executes approved actions safely
  evidence_verifier.py  Pass/fail on claimed_done evidence
  recovery.py           Engine-orchestrated recovery actions
  redactor.py           Deterministic secret redaction
  runbook.py            Declarative runbook runner (operator-authored)
  context_budget.py     Budgeted hierarchical context assembly
  project_facts.py      Read-only repo scan -> facts + excerpts
  markdown_view.py      Renders progress tracker from state
  config.py             Policy + allowlist (PyYAML, deep merge)
tests/                  stdlib unittest suite (240 tests)
scripts/run_supervised.py  End-to-end supervised demo (no LLM API)
example/                Standalone supervised demo (example project)
QUICKSTART.md           Three usage paths
ARCHITECTURE.md         Component + data-flow overview
SECURITY.md             Security model and defaults
LIMITATIONS.md          Honest limits of the release
EVALUATION.md           P8 evaluation results and how to rerun
pyproject.toml          Packaging metadata (no install needed to use)
LICENSE                 MIT
.github/workflows/      CI: test, lint, eval
docs/superpowers/       Design specs + implementation plans (Tahap 1-4)
skills/                 LHTM skill pack (planner, executor, verifier, ...)
policies/               security, action allowlist, completion rules
```

### Requirements

- Python 3.13 (stdlib `unittest` for tests)
- PyYAML (the only non-stdlib dependency, used by `engine/lhtm/config.py`)

### Quick start

Run the end-to-end supervised demo (simulated LLM, real gate + executor + verifier):

```bash
python scripts/run_supervised.py
```

Expected tail: T01 and T02 reach `verified_done`, T03 fails verification, then the
demo drives T03 through recovery (`retry_with_hint` -> `mark_blocked`) and renders a
redacted tracker.

Run the tests:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

### Install the skills

Install the six LHTM skills into any skill client (Claude Code, Antigravity,
Codex):

```bash
npx skills add ugihub/long-horizon-task
```

The engine is local Python; see `QUICKSTART.md` for the three usage paths.

### Using the engine programmatically

```python
from engine.lhtm.engine import LhtmEngine

engine = LhtmEngine(".lhtm")
engine.set_goal("Build a CLI todo app")
engine.load_plan(plan_dict)      # validated, goal_hash must match
engine.approve_plan()            # phase -> READY
engine.activate_task("T01")
engine.process_update(update)    # engine validates + verifies
engine.recover("T01", {"action": "retry_with_hint", "hint": "..."})
engine.render_tracker()
```

### Execution modes

| Mode | Mutating actions | Use |
|---|---|---|
| `DRY_RUN` | no-ops (marked `dry_run`, nothing executed) | rehearsal |
| `SUPERVISED` | always require approval | safe default |
| `AUTO_SAFE` | auto-approve only low-risk, non-sensitive | limited auto-run |
| `FULL_AUTO` | no approval required | highest trust |

`set_mode` validates the mode; `switch_to_safe_mode` can only lower the mode
(never to `FULL_AUTO`).

### Roadmap status

All sprints P0-P9 implemented: skill pack + output contract, stateful planning,
supervised executor, evidence verification, safe command execution, recovery &
robustness, security & context hardening, evaluation harness (P8), and public
release packaging (P9). Install the skill pack in Claude Code / Antigravity /
Codex with `npx skills add ugihub/long-horizon-task` (once the repo is public).
The repo is currently private; all release artifacts are present and verified.

---

## Bahasa Indonesia

### Apa itu LHTM?

LHTM mengubah "minta agen mengerjakan tugas multi-langkah yang besar" menjadi proses
terstruktur, teraudit, dan aman. Alih-alih mempercayai LLM, LHTM memisahkan kerja
antara **LLM yang mengusulkan** dan **engine deterministik yang memvalidasi dan
memutuskan**.

```
LLM proposes. Engine validates. Evidence decides.
JSON canonical state. Markdown hanya generated view.
Eksekusi terikat active_task_id.
Guardrail deterministik, bukan hanya prompt.
```

Engine tidak pernah percaya begitu saja pada model: setiap transisi state, penulisan
file, dan perintah harus lolos pemeriksaan deterministik, dan tidak ada task yang
menjadi `verified_done` tanpa bukti yang terverifikasi.

### Konsep inti

- **LLM mengusulkan, engine memvalidasi** - model mengirim update terstruktur; engine
  memeriksa skema, transisi legal, allowed paths, allowlist, dan pola destruktif
  sebelum apa pun diterapkan.
- **Bukti yang memutuskan** - `claimed_done` menjadi `verified_done` hanya jika
  verifikator bukti mengonfirmasi (file ada, di dalam allowed paths, definition of
  done terpenuhi).
- **JSON adalah sumber kebenaran** - state disimpan dalam JSON kanonik
  (`.lhtm/state.json`); tracker Markdown hanyalah tampilan yang di-generate.
- **Satu task aktif** - eksekusi terikat pada `active_task_id`; engine menolak update
  yang tidak berurutan.
- **Guardrail deterministik** - keamanan diberlakukan di kode (`action_gate`,
  `safe_executor`, `redactor`), bukan sekadar di prompt.
- **4 mode eksekusi** - `DRY_RUN`, `SUPERVISED`, `AUTO_SAFE`, `FULL_AUTO`. Default
  `supervised`. `AUTO_SAFE` meng-approve otomatis hanya aksi berisiko-rendah dan
  non-sensitif; `switch_to_safe_mode` hanya bisa menurunkan mode, tidak pernah naik
  ke `FULL_AUTO`.

### Fitur utama

- **Planning ber-state** - hash goal, validasi plan, 8 status task
  (`pending/ready/active/blocked/claimed_done/verified_done/failed/skipped`), tabel
  transisi legal.
- **Action gate** - memblokir write di luar scope, file sensitif (`.env`, `*.pem`,
  kredensial), perintah destruktif (`rm -rf`, `sudo`, `curl|bash`, force push), dan
  perintah yang tidak di-allowlist.
- **Safe executor** - `tool + args` terstruktur (tanpa raw shell secara default),
  backup saat overwrite, pemotongan output, timeout per perintah, dukungan dry-run.
- **Verifikasi bukti** - `claimed_done` -> `verified_done` hanya setelah verifikasi
  deterministik; kegagalan menghasilkan `failed` + feedback.
- **Recovery** (`P6`) - aksi yang diorchestrasi engine: `retry_with_hint`,
  `request_user_input`, `mark_blocked`, `decompose_task`, `rollback_proposal`,
  `switch_to_safe_mode`; setiap target adalah transisi yang legal.
- **Penguatan keamanan & konteks** (`P7`) - redaksi rahasia (khusus tampilan model),
  runbook runner (ditulis operator, idempotent), perakitan konteks beranggaran,
  pemindaian repo `project_facts`.

### Struktur repositori

```
engine/lhtm/            Engine deterministik (stdlib + PyYAML)
  engine.py             Fasade LhtmEngine (goal, plan, activate, recover, facts)
  state_store.py        Baca/tulis state atomik + snapshot
  schema_validator.py   Validasi state / plan / update / transisi
  task_scheduler.py     Memilih task berikutnya yang bisa dijalankan
  action_gate.py        Inti keamanan: cek path/command/approval
  safe_executor.py      Mengeksekusi aksi yang disetujui secara aman
  evidence_verifier.py  Pass/fail pada bukti claimed_done
  recovery.py           Aksi recovery yang diorchestrasi engine
  redactor.py           Redaksi rahasia deterministik
  runbook.py            Runner runbook deklaratif (ditulis operator)
  context_budget.py     Perakitan konteks hierarkis beranggaran
  project_facts.py      Pemindaian repo read-only -> facts + excerpts
  markdown_view.py      Merender tracker progres dari state
  config.py             Kebijakan + allowlist (PyYAML, deep merge)
tests/                  Suite stdlib unittest (240 tes)
scripts/run_supervised.py  Demo supervised end-to-end (tanpa API LLM)
example/                Demo supervised standalone (project contoh)
QUICKSTART.md           Tiga jalur pemakaian
ARCHITECTURE.md         Ringkasan komponen + data flow
SECURITY.md             Model keamanan dan default
LIMITATIONS.md          Batasan jujur rilis ini
EVALUATION.md           Hasil evaluasi P8 dan cara menjalankan ulang
pyproject.toml          Metadata packaging (tak perlu install untuk memakai)
LICENSE                 MIT
.github/workflows/      CI: test, lint, eval
docs/superpowers/       Spesifikasi desain + rencana implementasi (Tahap 1-4)
skills/                 Paket skill LHTM (planner, executor, verifier, ...)
policies/               security, action allowlist, completion rules
```

### Persyaratan

- Python 3.13 (stdlib `unittest` untuk tes)
- PyYAML (satu-satunya dependensi non-stdlib, dipakai `engine/lhtm/config.py`)

### Memulai cepat

Jalankan demo supervised end-to-end (LLM simulasi, gate + executor + verifier nyata):

```bash
python scripts/run_supervised.py
```

Hasil akhir: T01 dan T02 mencapai `verified_done`, T03 gagal verifikasi, lalu demo
mengarahkan T03 melalui recovery (`retry_with_hint` -> `mark_blocked`) dan merender
tracker teredaksi.

Jalankan tes:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

### Pasang skill

Pasang enam skill LHTM ke klien skill apa pun (Claude Code, Antigravity, Codex):

```bash
npx skills add ugihub/long-horizon-task
```

Engine adalah Python lokal; lihat `QUICKSTART.md` untuk tiga jalur pemakaian.

### Memakai engine secara programatik

```python
from engine.lhtm.engine import LhtmEngine

engine = LhtmEngine(".lhtm")
engine.set_goal("Build a CLI todo app")
engine.load_plan(plan_dict)      # divalidasi, goal_hash harus cocok
engine.approve_plan()            # fase -> READY
engine.activate_task("T01")
engine.process_update(update)    # engine memvalidasi + memverifikasi
engine.recover("T01", {"action": "retry_with_hint", "hint": "..."})
engine.render_tracker()
```

### Mode eksekusi

| Mode | Aksi mutasi | Kegunaan |
|---|---|---|
| `DRY_RUN` | no-op (ditandai `dry_run`, tidak ada yang dieksekusi) | latihan |
| `SUPERVISED` | selalu butuh approval | default aman |
| `AUTO_SAFE` | auto-approve hanya berisiko-rendah & non-sensitif | auto-run terbatas |
| `FULL_AUTO` | tanpa approval | kepercayaan tertinggi |

`set_mode` memvalidasi mode; `switch_to_safe_mode` hanya menurunkan mode (tidak pernah
ke `FULL_AUTO`).

### Status roadmap

Semua sprint P0-P9 sudah diimplementasikan: skill pack + kontrak output, planning
ber-state, executor supervised, verifikasi bukti, eksekusi perintah aman, recovery
& ketangguhan, penguatan keamanan & konteks, evaluation harness (P8), dan
packaging rilis publik (P9). Pasang skill pack di Claude Code / Antigravity /
Codex dengan `npx skills add ugihub/long-horizon-task` (setelah repo publik).
Saat ini repo masih privat; semua artefak rilis sudah lengkap dan terverifikasi.

---

## License

MIT. See `LICENSE`.
