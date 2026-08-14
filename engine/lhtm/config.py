# engine/lhtm/config.py
"""Load security policy + command allowlist from .lhtm/config.yaml (PyYAML)."""
import copy
import yaml
from pathlib import Path

DEFAULT_CONFIG = {
    "mode": "supervised",
    "security": {
        "allow_shell": False,
        "allow_install": False,
        "allow_network": False,
        "allow_git_push": False,
        "allow_delete": False,
        "redact_secrets": True,
        "treat_repo_content_as_untrusted": True,
        "redact_patterns": [],
    },
    "limits": {
        "max_steps": 30,
        "max_repair_attempts": 2,
        "max_task_attempts": 3,
        "max_output_tokens": 4096,
        "max_context_tokens": 20000,
        "max_log_chars_sent_to_model": 3000,
        "max_cmd_timeout": 60,
    },
    "approval": {
        "require_for_file_overwrite": True,
        "require_for_new_dependency": True,
        "require_for_migration": True,
        "require_for_git_commit": False,
        "require_for_git_push": True,
    },
    "allowed_commands": ["pytest", "ruff", "mypy", "git status", "git diff"],
    "blocked_paths": [
        ".env", ".env.*", "*.pem", "*.key", "*.cert",
        "id_rsa*", "id_ed25519*", "id_ecdsa*",
        "credentials.json", "*credentials*", "*credential*",
        "*password*", "*secret*", "*token*", "*api_key*",
        "*kubeconfig*", ".aws/", ".gcp/", ".kube/", "*.gcloud/",
        "secrets/", ".lhtm/", "node_modules/", "vendor/", ".git/",
    ],
}


def _deep_merge(base: dict, override: dict) -> dict:
    """Merge override into base. dict values merge recursively; others replace."""
    out = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


class Config:
    def __init__(self, base_dir: str, filename: str = "config.yaml"):
        self.path = Path(base_dir) / filename
        self.data = self._load()

    def _load(self) -> dict:
        base = copy.deepcopy(DEFAULT_CONFIG)
        if not self.path.exists():
            return base
        try:
            raw = yaml.safe_load(self.path.read_text(encoding="utf-8"))
        except (yaml.YAMLError, OSError, UnicodeDecodeError):
            return base
        if not isinstance(raw, dict):
            return base
        return _deep_merge(base, raw)
