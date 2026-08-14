# Completion Rules — Tahap 1

## When a task is done
1. All `definition_of_done` items are satisfied
2. Evidence is provided for each item
3. Paths used are within `allowed_paths`
4. Status changes to `claimed_done`

## Verification check (P4+)
- File existence
- Path within allowed
- Test results (if applicable)
- Evidence matches definition_of_done

## Anti-patterns
- Claiming done without evidence → rejected
- Claiming done for a task whose `depends_on` are not `verified_done` → rejected
- Skipping `definition_of_done` → rejected
