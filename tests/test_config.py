# tests/test_config.py
import os, tempfile, shutil, unittest
from engine.lhtm.config import Config

DEFAULT_MODE = "supervised"

class TestConfig(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_defaults_when_no_file(self):
        cfg = Config(self.tmp)
        self.assertEqual(cfg.data["mode"], DEFAULT_MODE)
        self.assertIn("security", cfg.data)
        self.assertIn("allowed_commands", cfg.data)
        self.assertFalse(cfg.data["security"]["allow_shell"])
        self.assertEqual(cfg.data["limits"]["max_log_chars_sent_to_model"], 3000)

    def test_loads_yaml_file(self):
        with open(os.path.join(self.tmp, "config.yaml"), "w", encoding="utf-8") as f:
            f.write("mode: full_auto\nsecurity:\n  allow_shell: true\n")
        cfg = Config(self.tmp)
        self.assertEqual(cfg.data["mode"], "full_auto")
        self.assertTrue(cfg.data["security"]["allow_shell"])
        # unspecified keys keep defaults
        self.assertEqual(cfg.data["limits"]["max_log_chars_sent_to_model"], 3000)

    def test_invalid_yaml_falls_back_to_defaults(self):
        with open(os.path.join(self.tmp, "config.yaml"), "w", encoding="utf-8") as f:
            f.write(": : : not yaml\n[[[")
        cfg = Config(self.tmp)
        self.assertEqual(cfg.data["mode"], DEFAULT_MODE)

    def test_config_path_custom(self):
        p = os.path.join(self.tmp, "custom.yaml")
        with open(p, "w", encoding="utf-8") as f:
            f.write("mode: auto_safe\n")
        cfg = Config(self.tmp, filename="custom.yaml")
        self.assertEqual(cfg.data["mode"], "auto_safe")

    def test_non_utf8_file_falls_back_to_defaults(self):
        with open(os.path.join(self.tmp, "config.yaml"), "wb") as f:
            f.write(b"mode: caf\xe9\n")  # latin-1 byte, not valid utf-8
        cfg = Config(self.tmp)
        self.assertEqual(cfg.data["mode"], DEFAULT_MODE)

    def test_default_config_not_aliased(self):
        from engine.lhtm.config import DEFAULT_CONFIG
        cfg = Config(self.tmp)  # no file -> deepcopy defaults
        cfg.data["limits"]["max_log_chars_sent_to_model"] = 999
        self.assertEqual(DEFAULT_CONFIG["limits"]["max_log_chars_sent_to_model"], 3000)


if __name__ == "__main__":
    unittest.main()
