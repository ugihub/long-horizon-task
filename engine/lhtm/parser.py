# engine/lhtm/parser.py
import re, json
from .schema_validator import SchemaValidator

MAX_REPAIR_ATTEMPTS = 2

class LhtmParser:
    def __init__(self):
        self._pattern = re.compile(r"```lhtm-update\s*\n(.*?)\n```", re.DOTALL)
        self._validator = SchemaValidator()

    def extract_updates(self, text: str) -> list[dict]:
        """Extract all lhtm-update fenced blocks from LLM output.
        Returns list of parsed dicts. On parse failure, returns dict with 'errors' key."""
        blocks = self._pattern.findall(text)
        results = []
        for block in blocks:
            parsed = self._try_parse(block.strip())
            if "errors" in parsed:
                results.append(parsed)
                continue
            # validate against schema
            errs = self._validator.validate_update(parsed)
            if errs:
                parsed["errors"] = errs
            results.append(parsed)
        return results

    def _try_parse(self, text: str) -> dict:
        for attempt in range(MAX_REPAIR_ATTEMPTS + 1):
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                text = self.repair_json(text)
        return {"errors": [f"Failed to parse JSON after {MAX_REPAIR_ATTEMPTS} repair attempts"]}

    def repair_json(self, text: str) -> str:
        """Deterministic JSON repair. Max 2 heuristics."""
        # 1. Remove trailing commas before closing
        text = re.sub(r",\s*([}\]])", r"\1", text)
        # 2. Fix unclosed quotes at end
        if text.count('"') % 2 != 0:
            text += '"'
        # 3. Balance braces
        opens = text.count("{")
        closes = text.count("}")
        if opens > closes:
            text += "}" * (opens - closes)
        return text
