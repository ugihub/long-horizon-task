# tests/test_redactor.py
import unittest
from engine.lhtm.redactor import Redactor
from engine.lhtm.config import DEFAULT_CONFIG


class TestRedactor(unittest.TestCase):
    def test_redacts_value_not_key(self):
        r = Redactor()
        out = r.redact("password: hunter2\napi_key = abc123")
        self.assertNotIn("hunter2", out)
        self.assertNotIn("abc123", out)
        self.assertIn("password: [REDACTED]", out)
        self.assertIn("api_key = [REDACTED]", out)

    def test_redacts_inline_hex(self):
        r = Redactor()
        out = r.redact("token is 9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08")
        self.assertIn("[REDACTED]", out)
        self.assertNotIn("9f86d081", out)

    def test_does_not_redact_plain_word(self):
        # bare keyword with no value is left alone
        r = Redactor()
        out = r.redact("set the token before running")
        self.assertEqual(out, "set the token before running")

    def test_redact_path_sensitive(self):
        r = Redactor()
        self.assertEqual(r.redact_path("config/.env"), "[REDACTED]")
        self.assertEqual(r.redact_path("certs/server.pem"), "[REDACTED]")

    def test_redact_path_clean(self):
        r = Redactor()
        self.assertEqual(r.redact_path("src/app.py"), "src/app.py")

    def test_custom_pattern(self):
        r = Redactor(text_patterns=["vault_key"])
        out = r.redact("vault_key: s3cr3t")
        self.assertIn("[REDACTED]", out)
        self.assertNotIn("s3cr3t", out)

    def test_from_config_merges_extra_patterns(self):
        cfg = dict(DEFAULT_CONFIG)
        cfg["security"]["redact_patterns"] = ["github_pat"]
        r = Redactor.from_config(cfg)
        out = r.redact("github_pat: ghp_12345")
        self.assertIn("[REDACTED]", out)

    def test_empty_input(self):
        self.assertEqual(Redactor().redact(""), "")


if __name__ == "__main__":
    unittest.main()
