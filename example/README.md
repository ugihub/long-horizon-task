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
