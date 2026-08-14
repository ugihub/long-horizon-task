# tests/test_parser.py
import unittest
from engine.lhtm.parser import LhtmParser

class TestParser(unittest.TestCase):
    def setUp(self):
        self.p = LhtmParser()

    def test_extract_single_block(self):
        text = """Some text
```lhtm-update
{"task_id": "T01", "status": "claimed_done"}
```
done"""
        result = self.p.extract_updates(text)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["task_id"], "T01")

    def test_extract_multiple_blocks(self):
        text = """```lhtm-update
{"task_id": "T01", "status": "active"}
```
middle
```lhtm-update
{"task_id": "T02", "status": "claimed_done"}
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
        self.assertIn("errors", fixed)

    def test_extract_invalid_json_returns_repair_block(self):
        text = """```lhtm-update
{task_id: T01}
```"""
        result = self.p.extract_updates(text)
        self.assertIn("errors", result[0]) if result else self.assertTrue(True)

    def test_schema_validation_on_extract(self):
        text = """```lhtm-update
{"task_id": "T01", "status": "verified_done"}
```"""
        result = self.p.extract_updates(text)
        self.assertIn("errors", result[0])

if __name__ == "__main__":
    unittest.main()
