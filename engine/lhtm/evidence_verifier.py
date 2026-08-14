# engine/lhtm/evidence_verifier.py
"""Deterministic evidence verification: claimed_done -> verified_done only with proof."""
from pathlib import Path

from .action_gate import _path_allowed


def _ev_text(ev: dict) -> str:
    """Concatenated evidence text used for definition-of-done coverage."""
    return f"{ev.get('note', '')} {ev.get('path', '')} {ev.get('type', '')}"


def _covered(do_item: str, evs: list) -> bool:
    """True if a DoD item is covered by any evidence.

    Match is deterministic: the full item (lowercased) is a substring of some
    evidence's note+path+type, OR at least one 3+ char token of the item appears
    in some evidence's text.
    """
    item = do_item.lower()
    for e in evs:
        if item in _ev_text(e).lower():
            return True
    tokens = [t for t in item.split() if len(t) >= 3]
    return any(any(t in _ev_text(e).lower() for e in evs) for t in tokens)


class EvidenceVerifier:
    def verify(self, state: dict, task: dict, config: dict) -> dict:
        """Return {'verdict': 'pass'|'fail', 'feedback': str|None, 'checks': [str]}.

        Deterministic checks, in order:
          C1 evidence present
          C2 every evidence path (and artifact) within task allowed_paths
          C3 every file_created path / artifact exists on disk
          C4 every definition_of_done item covered by some evidence
          C5 test_pass evidence present when a DoD item mentions tests

        `config` is reserved for future coupling (max_repair_attempts) and
        currently unused. No LLM, no external calls.
        """
        checks = []
        evs = task.get("evidence", []) or []
        artifacts = task.get("artifacts", []) or []
        allowed = task.get("allowed_paths", []) or []
        dod = task.get("definition_of_done", []) or []

        if not evs:
            return {"verdict": "fail", "feedback": "no evidence provided",
                    "checks": ["C1 evidence: FAIL (none)"]}
        checks.append("C1 evidence: PASS")

        info_paths = [e["path"] for e in evs if e.get("path")]
        file_paths = list({e["path"] for e in evs if e.get("type") == "file_created" and e.get("path")})
        file_paths += [a for a in artifacts if isinstance(a, str) and a not in file_paths]

        bad = [p for p in info_paths if not _path_allowed(p, allowed)]
        if bad:
            return {"verdict": "fail",
                    "feedback": "path(s) outside allowed_paths: " + ", ".join(bad),
                    "checks": checks + ["C2 paths: FAIL"]}
        checks.append("C2 paths: PASS")

        missing = [p for p in file_paths if not Path(p).exists()]
        if missing:
            return {"verdict": "fail",
                    "feedback": "file(s) missing: " + ", ".join(missing),
                    "checks": checks + ["C3 files: FAIL"]}
        checks.append("C3 files: PASS")

        for d in dod:
            if not _covered(d, evs):
                return {"verdict": "fail",
                        "feedback": f"definition_of_done not covered: '{d}'",
                        "checks": checks + ["C4 coverage: FAIL"]}
        checks.append("C4 coverage: PASS")

        if any(any(k in d.lower() for k in ("test", "pass", "lint", "check")) for d in dod):
            if not any(e.get("type") == "test_pass" for e in evs):
                return {"verdict": "fail",
                        "feedback": "definition_of_done mentions tests but no test_pass evidence",
                        "checks": checks + ["C5 tests: FAIL"]}
            checks.append("C5 tests: PASS")

        return {"verdict": "pass", "feedback": None, "checks": checks}
