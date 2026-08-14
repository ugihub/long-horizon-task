# engine/lhtm/redactor.py
"""Deterministic secret redaction for model-facing output. Never persisted state."""
import fnmatch
import re

FILE_SECRET_PATTERNS = [".env", ".env.*", "*.pem", "*.key", "*.cert", "*.crt"]
KEYWORD_SECRET_PATTERNS = [
    "api_key", "apikey", "password", "passwd", "secret",
    "token", "client_secret", "access_token",
]
PLACEHOLDER = "[REDACTED]"

_LONG_HEX = re.compile(r"\b[0-9a-f]{32,64}\b", re.IGNORECASE)
_LONG_B64 = re.compile(r"\b[A-Za-z0-9+/]{22,}={0,2}\b")


class Redactor:
    def __init__(self, text_patterns=None, file_patterns=None, placeholder=PLACEHOLDER):
        self.text_patterns = list(text_patterns) if text_patterns is not None else list(KEYWORD_SECRET_PATTERNS)
        self.file_patterns = list(file_patterns) if file_patterns is not None else list(FILE_SECRET_PATTERNS)
        self.placeholder = placeholder
        # key: value and key = value redaction. Word-boundary anchored so 'secret'
        # does not match inside 'client_secret' (underscore is a word char).
        # The separator (":" or "=") and any leading space are captured and
        # preserved in the output.
        self._pairs = [
            re.compile(r"(?i)\b({})\b(\s*)([:=])\s*([\"']?)([^\"'\s,;]+)\4".format(re.escape(p)))
            for p in self.text_patterns
        ]

    @classmethod
    def from_config(cls, config):
        extra = config.get("security", {}).get("redact_patterns", []) or []
        return cls(text_patterns=KEYWORD_SECRET_PATTERNS + list(extra))

    def redact(self, text: str) -> str:
        if not text:
            return text
        for rx in self._pairs:
            text = rx.sub(lambda m: m.group(1) + m.group(2) + m.group(3) + " " + self.placeholder, text)
        text = _LONG_HEX.sub(self.placeholder, text)
        text = _LONG_B64.sub(self.placeholder, text)
        return text

    def redact_path(self, path: str) -> str:
        low = path.replace("\\", "/").lower()
        for pat in self.file_patterns:
            p = pat.lower()
            if p in low or fnmatch.fnmatch(low, p) or fnmatch.fnmatch(low, p + "*"):
                return self.placeholder
        return path
