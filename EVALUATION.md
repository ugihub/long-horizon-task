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
