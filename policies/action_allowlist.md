# Action Allowlist -- Tahap 1

## Permitted (in Tahap 1, human executes)
- READ: any file under `allowed_paths`
- ANALYZE: propose refactoring, review code
- PLAN: generate plan JSON, decompose tasks
- QUESTION: ask user for clarification

## NOT Permitted (Tahap 1)
- WRITE files (P3+)
- DELETE files (P3+)
- RUN shell commands (P5+)
- ACCESS secrets (P7+)
