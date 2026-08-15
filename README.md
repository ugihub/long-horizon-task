# LHTM v2

**L**ong **H**orizon **T**ask **M**anager - a deterministic, engine-driven framework for
executing long-running agentic tasks safely and verifiably.

**LHTM v2** - kerangka kerja deterministik yang dijalankan oleh engine untuk mengeksekusi
tugas agen jangka panjang secara aman dan terverifikasi.

> **English** | [Bahasa Indonesia](#bahasa-indonesia)

**tags:** `llm-agents` `guardrails` `deterministic-engine` `task-management` `agentic-ai`
`evidence-based` `evaluation` `claude-code` `skills-sh` `python`

---

## English

### What is LHTM?

LHTM turns "ask an agent to do a big multi-step task" into a structured, auditable,
safe process. Instead of trusting the LLM to behave, LHTM splits the work between an
**LLM that proposes** and a **deterministic engine that validates and decides**.

LHTM is boring on purpose. It never takes the model's word for anything: every state
transition, file write, and command must pass deterministic checks, and no task becomes
`verified_done` without verifiable evidence. The cage is built in code, not in prompts.

```
LLM proposes. Engine validates. Evidence decides.
JSON canonical state. Markdown is only a generated view.
Execution is bound to active_task_id.
Deterministic guardrails, not just prompts.
```

### The LHTM cycle

This is the whole project in one diagram - the alur the engine runs every session.

```
    GOAL        you state it once; engine hashes + freezes it
     |
     v
    PLAN        planner proposes JSON (schema lhtm.plan/v1); engine validates
     |            schema, task fields, dependencies, cycle-free, goal_hash match
     v
    READY       approved; scheduler promotes exactly one task at a time
     |
     v
    EXECUTE     one active_task_id; you emit lhtm-update blocks
     |            action gate + safe executor run only approved actions
     v
    VERIFY      claimed_done -> evidence verifier (C1-C5)
     |            pass -> verified_done   fail -> failed + feedback
     v
    RECOVER     retry / decompose / mark_blocked / rollback / ask user
     |
     v
    DONE        all tasks terminal; redacted tracker rendered
```

Every arrow is a deterministic engine check. Nothing moves to the next stage without
passing it.

### Design philosophy

- **The model proposes, never decides.** Statuses like `verified_done` are engine-owned.
- **Evidence over claims.** A task is done only when its `definition_of_done` is proven.
- **Safe by default.** `supervised` is the default mode - writes and commands ask approval.
- **Auditable everything.** State, events, and redacted views are generated, never hand-edited.
- **Boring beats clever.** Predictable, testable, CI-friendly. No magic.

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
- **Evaluation harness** (`P8`) - static adversarial fixtures drive the real engine;
  5 metrics vs task.md targets, written to `eval/report.md`.

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
tests/                  stdlib unittest suite (242 tests)
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

### Detailed usage

#### 1. Install

```bash
python -m pip install PyYAML
```

That is the entire dependency list. Everything else is the Python standard library.

#### 2. Run the supervised demo

```bash
python scripts/run_supervised.py
```

What you will see:

1. The goal is set and hashed; the plan is approved and the phase moves to READY.
2. T01 and T02 reach `verified_done` - the gate approves their writes, the executor
   writes `src/cli.py` and `src/parser.py`, and the evidence verifier confirms the
   files exist.
3. T03 claims a file that was never created. Verification fails and the task becomes
   `failed` with feedback.
4. Recovery drives T03 through `retry_with_hint` then `mark_blocked`.
5. A redacted progress tracker is rendered.

The demo is non-interactive (approvals are auto-granted so it can run in CI), uses a
simulated LLM (no API, no cost), and cleans up its temp state and `src/` when done.

#### 3. Run the tests

```bash
python -m unittest discover -s tests -p "test_*.py"
```

242 tests, all stdlib `unittest`. No pytest required.

#### 4. Run the evaluation harness

```bash
python -m eval
```

Runs 8 adversarial fixture scenarios against the real engine (gate + executor +
verifier + recovery), writes `eval/report.md`, and exits 0 only if all 5 metrics
meet the task.md targets. Use it as a regression gate: a broken guardrail flips
`passed` to false. See `EVALUATION.md`.

#### 5. Drive the engine programmatically

```python
from engine.lhtm.engine import LhtmEngine
from engine.lhtm.config import Config
from engine.lhtm.task_scheduler import TaskScheduler
from engine.lhtm.action_gate import ActionGate
from engine.lhtm.safe_executor import SafeExecutor
import tempfile, shutil

base = tempfile.mkdtemp(prefix="lhtm-")                 # engine state lives here
engine = LhtmEngine(base)
cfg = Config(base)                                      # loads defaults from config.yaml
engine.set_goal("Build a CLI todo app")                 # hashed + frozen
engine.state["mode"] = cfg.data["mode"].upper()         # 'supervised' by default
scheduler = TaskScheduler()
gate = ActionGate()
executor = SafeExecutor(cfg.data)

plan = {
    "schema_version": "1.0",
    "run_id": engine.state["run_id"],
    "goal_hash": engine.state["goal"]["hash"],
    "title": "Todo App",
    "objective": "Build a CLI todo app",
    "tasks": [{
        "id": "T01", "title": "Scaffold", "objective": "Init cli.py",
        "status": "pending", "depends_on": [], "risk_level": "low",
        "allowed_paths": ["src/"], "allowed_commands": ["python"],
        "definition_of_done": ["cli.py exists"], "artifacts": [],
        "evidence": [], "attempts": 0, "max_attempts": 3,
    }],
    "open_questions": [], "metadata": {}, "approved": False,
}
engine.load_plan(plan)                  # validates schema, fields, goal_hash
engine.approve_plan()                   # phase -> READY
scheduler.promote_to_ready(engine.state, "T01")   # pending -> ready
engine._save()
engine.activate_task("T01")

update = {
    "task_id": "T01",
    "status": "claimed_done",
    "evidence": [{"type": "file_created", "path": "src/cli.py", "note": "cli.py exists"}],
    "artifacts": ["src/cli.py"],
    "proposed_actions": [{"action": "write_file", "path": "src/cli.py",
                          "content": "print('todo app v1')\n"}],
}

# 1. gate + execute each proposed action (the engine validates, never the model)
task = next(t for t in engine.state["tasks"] if t["id"] == "T01")
for action in update["proposed_actions"]:
    decision = gate.check(action, task, cfg.data, engine.state["mode"], task["id"])
    if decision["allowed"]:
        executor.execute(action, {**decision, "approval_granted": True}, task)

# 2. let the engine verify the claimed_done evidence
result = engine.process_update(update)
print(result["verdict"])                 # 'pass' -> status becomes verified_done
print(result["feedback"])                # verifier feedback (when fail)
print(task["status"])                    # 'verified_done'

print(engine.render_tracker())           # generated markdown view
shutil.rmtree("src", ignore_errors=True)
shutil.rmtree(base, ignore_errors=True)
```

#### 6. Write your own plan

A plan is JSON, schema `lhtm.plan/v1`. The rules the engine enforces:

- Task IDs are `T01`, `T02`, ...
- `depends_on` must reference existing task IDs and be cycle-free.
- All tasks start `pending`.
- `allowed_paths` are relative paths - the gate rejects anything outside them.
- `definition_of_done` items must be specific and verifiable ("cli.py exists", not "finish the app").
- `risk_level`: `low` = read-only, `medium` = file edit, `high` = destructive command.
- `goal_hash` must equal `engine.state["goal"]["hash"]` or the plan is rejected.

The full shape is documented in `skills/planner/SKILL.md`.

#### 7. Install the skills

Install the six LHTM skills into any skill client (Claude Code, Antigravity, Codex):

```bash
npx skills add ugihub/long-horizon-task
```

This installs `lhtm-core`, `planner`, `executor`, `verifier`, `recovery`,
`output-contract`. The model reads the rules and drives the protocol; the engine
(step 5) enforces it deterministically. The engine is local Python - skill clients
cannot run it, so install the repo on the machine doing the work.

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

LHTM membosankan dengan sengaja. Engine tidak pernah percaya begitu saja pada model:
setiap transisi state, penulisan file, dan perintah harus lolos pemeriksaan
deterministik, dan tidak ada task yang menjadi `verified_done` tanpa bukti yang
terverifikasi. Kandang keamanannya dibangun di kode, bukan di prompt.

```
LLM proposes. Engine validates. Evidence decides.
JSON canonical state. Markdown hanya generated view.
Eksekusi terikat active_task_id.
Guardrail deterministik, bukan hanya prompt.
```

### Alur proyek (LHTM cycle)

Inilah seluruh proyek dalam satu diagram - alur yang dijalankan engine di setiap sesi.

```
    GOAL        goal dinyatakan sekali; engine menghash + membekukannya
     |
     v
    PLAN        planner mengusulkan JSON (skema lhtm.plan/v1); engine memvalidasi
     |            skema, field task, dependensi, bebas-siklus, kecocokan goal_hash
     v
    READY       disetujui; scheduler mempromosikan tepat satu task pada satu waktu
     |
     v
    EXECUTE     satu active_task_id; kamu mengirim blok lhtm-update
     |            action gate + safe executor hanya menjalankan aksi yang disetujui
     v
    VERIFY      claimed_done -> verifikator bukti (C1-C5)
     |            lolos -> verified_done   gagal -> failed + feedback
     v
    RECOVER     retry / decompose / mark_blocked / rollback / tanya user
     |
     v
    DONE        semua task terminal; tracker teredaksi dirender
```

Setiap panah adalah pemeriksaan engine yang deterministik. Tidak ada yang pindah ke
tahap berikutnya tanpa lolos pemeriksaan itu.

### Filosofi desain

- **Model mengusulkan, tidak pernah memutuskan.** Status seperti `verified_done`
  dimiliki engine.
- **Bukti mengalahkan klaim.** Sebuah task selesai hanya jika `definition_of_done`-nya
  terbukti.
- **Aman secara default.** `supervised` adalah mode default - write dan perintah
  meminta persetujuan.
- **Semuanya dapat diaudit.** State, event, dan tampilan teredaksi di-generate,
  tidak pernah diedit manual.
- **Bosan mengalahkan cerdik.** Dapat diprediksi, dapat diuji, ramah CI. Tanpa sulap.

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
- **Evaluation harness** (`P8`) - fixture adversarial statis menggerakkan engine asli;
  5 metrik terhadap target task.md, ditulis ke `eval/report.md`.

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
tests/                  Suite stdlib unittest (242 tes)
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

### Pemakaian detail

#### 1. Instalasi

```bash
python -m pip install PyYAML
```

Itu seluruh daftar dependensi. Sisanya murni pustaka standar Python.

#### 2. Jalankan demo supervised

```bash
python scripts/run_supervised.py
```

Yang akan kamu lihat:

1. Goal ditetapkan dan di-hash; plan disetujui dan fase berpindah ke READY.
2. T01 dan T02 mencapai `verified_done` - gate menyetujui write-nya, executor menulis
   `src/cli.py` dan `src/parser.py`, dan verifikator bukti mengonfirmasi file ada.
3. T03 mengklaim file yang tidak pernah dibuat. Verifikasi gagal dan task menjadi
   `failed` dengan feedback.
4. Recovery menggerakkan T03 melalui `retry_with_hint` lalu `mark_blocked`.
5. Tracker progres teredaksi dirender di akhir.

Demo non-interaktif (persetujuan diberikan otomatis agar bisa jalan di CI), memakai
LLM simulasi (tanpa API, tanpa biaya), dan membersihkan state sementara serta `src/`
setelah selesai.

#### 3. Jalankan tes

```bash
python -m unittest discover -s tests -p "test_*.py"
```

242 tes, semua `unittest` stdlib. Tanpa pytest.

#### 4. Jalankan evaluation harness

```bash
python -m eval
```

Menjalankan 8 skenario fixture adversarial terhadap engine asli (gate + executor +
verifier + recovery), menulis `eval/report.md`, dan keluar dengan kode 0 hanya jika
semua 5 metrik memenuhi target task.md. Pakai sebagai gerbang regresi: guardrail yang
rusak akan membalik `passed` menjadi false. Lihat `EVALUATION.md`.

#### 5. Menggerakkan engine secara programatik

```python
from engine.lhtm.engine import LhtmEngine
from engine.lhtm.config import Config
from engine.lhtm.task_scheduler import TaskScheduler
from engine.lhtm.action_gate import ActionGate
from engine.lhtm.safe_executor import SafeExecutor
import tempfile, shutil

base = tempfile.mkdtemp(prefix="lhtm-")                 # state engine disimpan di sini
engine = LhtmEngine(base)
cfg = Config(base)                                      # memuat default dari config.yaml
engine.set_goal("Build a CLI todo app")                 # di-hash + dibekukan
engine.state["mode"] = cfg.data["mode"].upper()         # 'supervised' secara default
scheduler = TaskScheduler()
gate = ActionGate()
executor = SafeExecutor(cfg.data)

plan = {
    "schema_version": "1.0",
    "run_id": engine.state["run_id"],
    "goal_hash": engine.state["goal"]["hash"],
    "title": "Todo App",
    "objective": "Build a CLI todo app",
    "tasks": [{
        "id": "T01", "title": "Scaffold", "objective": "Init cli.py",
        "status": "pending", "depends_on": [], "risk_level": "low",
        "allowed_paths": ["src/"], "allowed_commands": ["python"],
        "definition_of_done": ["cli.py exists"], "artifacts": [],
        "evidence": [], "attempts": 0, "max_attempts": 3,
    }],
    "open_questions": [], "metadata": {}, "approved": False,
}
engine.load_plan(plan)                  # memvalidasi skema, field, goal_hash
engine.approve_plan()                   # fase -> READY
scheduler.promote_to_ready(engine.state, "T01")   # pending -> ready
engine._save()
engine.activate_task("T01")

update = {
    "task_id": "T01",
    "status": "claimed_done",
    "evidence": [{"type": "file_created", "path": "src/cli.py", "note": "cli.py exists"}],
    "artifacts": ["src/cli.py"],
    "proposed_actions": [{"action": "write_file", "path": "src/cli.py",
                          "content": "print('todo app v1')\n"}],
}

# 1. gate + eksekusi setiap aksi yang diusulkan (engine yang memvalidasi, bukan model)
task = next(t for t in engine.state["tasks"] if t["id"] == "T01")
for action in update["proposed_actions"]:
    decision = gate.check(action, task, cfg.data, engine.state["mode"], task["id"])
    if decision["allowed"]:
        executor.execute(action, {**decision, "approval_granted": True}, task)

# 2. biarkan engine memverifikasi bukti claimed_done
result = engine.process_update(update)
print(result["verdict"])                 # 'pass' -> status menjadi verified_done
print(result["feedback"])                # feedback verifikator (saat fail)
print(task["status"])                    # 'verified_done'

print(engine.render_tracker())           # tampilan markdown yang di-generate
shutil.rmtree("src", ignore_errors=True)
shutil.rmtree(base, ignore_errors=True)
```

#### 6. Menulis plan sendiri

Plan adalah JSON, skema `lhtm.plan/v1`. Aturan yang ditegakkan engine:

- ID task adalah `T01`, `T02`, ...
- `depends_on` harus merujuk ID task yang ada dan bebas-siklus.
- Semua task mulai `pending`.
- `allowed_paths` adalah path relatif - gate menolak apa pun di luar itu.
- Item `definition_of_done` harus spesifik dan bisa diverifikasi ("cli.py exists",
  bukan "selesaiin aplikasinya").
- `risk_level`: `low` = read-only, `medium` = edit file, `high` = perintah destruktif.
- `goal_hash` harus sama dengan `engine.state["goal"]["hash"]` atau plan ditolak.

Bentuk lengkap didokumentasikan di `skills/planner/SKILL.md`.

#### 7. Pasang skill

Pasang enam skill LHTM ke klien skill apa pun (Claude Code, Antigravity, Codex):

```bash
npx skills add ugihub/long-horizon-task
```

Ini memasang `lhtm-core`, `planner`, `executor`, `verifier`, `recovery`,
`output-contract`. Model membaca aturannya dan menjalankan protokol; engine (langkah
5) menegakkannya secara deterministik. Engine adalah Python lokal - klien skill tidak
bisa menjalankannya, jadi instal repo di mesin yang mengerjakan tugas.

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
