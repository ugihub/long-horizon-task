# Security Policy — Tahap 1

## Scope
This policy defines the security model for LHTM. Enforcement starts at P3 (action_gate).
Tahap 1 (P0–P2) documents the schema only.

## Secret Patterns (blocked from read/write in P3+)
- `*.pem`, `*.key`, `*.cert`
- `.env`, `.env.*`
- `*credentials*`, `*credential*`
- `*password*`, `*secret*`, `*token*`, `*api_key*`
- `*id_rsa*`, `*id_ecdsa*`
- `*kubeconfig*`, `*aws/credentials*`, `*.gcloud/*`

## Path Blocklist (P3+)
- `.lhtm/` (engine state directory)
- `node_modules/`, `vendor/`, `.git/`
- System paths: `/etc/`, `/usr/`, `C:\Windows\`

## Command Denylist (P5+)
- `rm -rf /`, `rm -rf *`, `rm -rf .`
- `sudo`, `su`, `chmod 777`, `chown`
- `curl | bash`, `wget -O - | sh`
- `git push --force`, `git push -f`
- `DROP DATABASE`, `DROP TABLE`, `TRUNCATE`
- `:(){ :|:& };:`, `fork bomb`
