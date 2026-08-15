# tests/test_parser.py
import unittest
from engine.lhtm.parser import LhtmParser, PARSE_ERROR_KEY


class TestParser(unittest.TestCase):
    def setUp(self):
        self.p = LhtmParser()

    def test_extract_single_block(self):
        text = """Some text
```lhtm-update
{"task_id": "T01", "status": "claimed_done", "evidence": [{"type": "test", "path": "x"}]}
```
done"""
        result = self.p.extract_updates(text)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["task_id"], "T01")
        self.assertNotIn(PARSE_ERROR_KEY, result[0])

    def test_extract_multiple_blocks(self):
        text = """```lhtm-update
{"task_id": "T01", "status": "blocked"}
```
middle
```lhtm-update
{"task_id": "T02", "status": "ready"}
```"""
        result = self.p.extract_updates(text)
        self.assertEqual(len(result), 2)

    def test_no_block_returns_empty(self):
        result = self.p.extract_updates("just text")
        self.assertEqual(result, [])

    def test_repair_trailing_comma(self):
        fixed = self.p.repair_json('{"a": 1,}')
        self.assertEqual(fixed, '{"a": 1}')

    def test_repair_unclosed_quotes(self):
        fixed = self.p.repair_json('{"a": "hello}')
        self.assertIn("hello", fixed)

    def test_repair_will_not_attempt_beyond_max(self):
        # badly malformed; retry-exhaustion lives in _try_parse, not repair_json (str->str)
        fixed = self.p._try_parse("{bad")
        self.assertIn(PARSE_ERROR_KEY, fixed)

    def test_extract_invalid_json_returns_repair_block(self):
        text = """```lhtm-update
{task_id: T01}
```"""
        result = self.p.extract_updates(text)
        self.assertEqual(len(result), 1)
        self.assertIn(PARSE_ERROR_KEY, result[0])

    def test_schema_validation_on_extract(self):
        text = """```lhtm-update
{"task_id": "T01", "status": "verified_done"}
```"""
        result = self.p.extract_updates(text)
        self.assertEqual(len(result), 1)
        self.assertIn(PARSE_ERROR_KEY, result[0])

    def test_scalar_root_not_crash(self):
        # LLM emits a JSON array/scalar instead of an object -> parse_error, no crash
        for bad in ("[1,2]", "123", '"hi"'):
            text = f"```lhtm-update\n{bad}\n```"
            result = self.p.extract_updates(text)
            self.assertEqual(len(result), 1)
            self.assertIn(PARSE_ERROR_KEY, result[0])

    def test_comma_inside_string_not_removed(self):
        # string containing ',}' must be preserved, trailing comma still removed
        fixed = self.p.repair_json('{"x": ",}", "y": 1,}')
        self.assertEqual(fixed, '{"x": ",}", "y": 1}')

    def test_escaped_quote_not_counted_as_unclosed(self):
        # valid JSON with an escaped quote should not gain a spurious trailing quote
        fixed = self.p.repair_json('{"a": "he\\"llo"}')
        self.assertEqual(fixed, '{"a": "he\\"llo"}')

    def test_parse_error_key_does_not_shadow_user_json(self):
        # a block whose JSON legitimately contains a "parse_error" key is NOT
        # treated as a parse failure -- the sentinel distinguishes them.
        text = '```lhtm-update\n{"task_id": "T01", "status": "blocked", "parse_error": "x"}\n```'
        result = self.p.extract_updates(text)
        self.assertEqual(len(result), 1)
        # the user's key survives; it is not the failure sentinel value
        self.assertEqual(result[0][PARSE_ERROR_KEY], "x")

    def test_crlf_fences(self):
        text = "```lhtm-update\r\n{\"task_id\": \"T01\", \"status\": \"active\"}\r\n```"
        result = self.p.extract_updates(text)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["task_id"], "T01")

    def test_block_at_end_without_trailing_newline(self):
        text = "text\n```lhtm-update\n{\"task_id\": \"T01\", \"status\": \"active\"}\n```"
        result = self.p.extract_updates(text)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["task_id"], "T01")

if __name__ == "__main__":
    unittest.main()
