# engine/lhtm/parser.py
"""Deterministic extraction of lhtm-update fenced blocks from LLM output."""
import re
import json

from .schema_validator import SchemaValidator

MAX_REPAIR_ATTEMPTS = 2
PARSE_ERROR_KEY = "parse_error"
# sentinel marking a genuine parse failure (distinct from user JSON that
# happens to contain a "parse_error" key)
PARSE_FAILURE = object()


class LhtmParser:
    def __init__(self):
        self._pattern = re.compile(r"```lhtm-update[ \t]*\r?\n(.*?)\r?\n```", re.DOTALL)
        self._validator = SchemaValidator()

    def extract_updates(self, text: str) -> list[dict]:
        """Extract all lhtm-update fenced blocks from LLM output.

        Returns a list of parsed dicts. A dict that fails to parse or validate
        carries a ``parse_error`` list (with sentinel value); valid results never do.
        """
        blocks = self._pattern.findall(text)
        results = []
        for block in blocks:
            parsed = self._try_parse(block.strip())
            if parsed.get(PARSE_ERROR_KEY) is PARSE_FAILURE:
                # replace sentinel with a human-readable list before returning
                parsed[PARSE_ERROR_KEY] = ["Failed to parse JSON block"]
                results.append(parsed)
                continue
            # validate against schema
            errs = self._validator.validate_update(parsed)
            if errs:
                parsed[PARSE_ERROR_KEY] = errs
            results.append(parsed)
        return results

    def _try_parse(self, text: str) -> dict:
        for attempt in range(MAX_REPAIR_ATTEMPTS + 1):
            try:
                result = json.loads(text)
                if isinstance(result, dict):
                    return result
                return {PARSE_ERROR_KEY: PARSE_FAILURE}
            except json.JSONDecodeError:
                text = self.repair_json(text)
        return {PARSE_ERROR_KEY: PARSE_FAILURE}

    def repair_json(self, text: str) -> str:
        """Deterministic JSON repair heuristics. Best-effort; may not fix all."""
        # 1. Remove trailing commas before closers (outside of strings)
        text = self._strip_strings_and_fix_trailing_commas(text)
        # 2. Fix unclosed quotes at end
        if self._count_unescaped_quotes(text) % 2 != 0:
            text += '"'
        # 3. Balance braces
        opens = text.count("{")
        closes = text.count("}")
        if opens > closes:
            text += "}" * (opens - closes)
        return text

    @staticmethod
    def _count_unescaped_quotes(text: str) -> int:
        """Count double-quotes that are not escaped with a backslash."""
        count = 0
        escaped = False
        for ch in text:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                count += 1
        return count

    @staticmethod
    def _strip_strings_and_fix_trailing_commas(text: str) -> str:
        """Delete trailing commas before `}`/`]` that appear outside string literals.

        String-aware: string contents are masked out (replaced by spaces) so comma
        patterns inside strings are untouched. Commas found in non-string regions
        are deleted outright (not replaced with a space).
        """
        # build a mask: non-string chars keep their char, string contents -> space
        masked = []
        in_string = False
        escaped = False
        for ch in text:
            if escaped:
                escaped = False
                masked.append(" ")
                continue
            if ch == "\\":
                escaped = True
                masked.append(" ")
                continue
            if ch == '"':
                in_string = not in_string
                masked.append(ch)
            elif not in_string:
                masked.append(ch)
            else:
                masked.append(" ")
        masked_str = "".join(masked)
        # delete commas that precede a closer in the masked (non-string) text
        out = list(text)
        for m in re.finditer(r",\s*([}\]])", masked_str):
            for i in range(m.start(), m.end()):
                if out[i] == ",":
                    out[i] = ""
        return "".join(out)
