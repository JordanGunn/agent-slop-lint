"""Identity and staleness for a finding.

``code_fingerprint`` changes when the code shown or the rubric changes, which is when an
earlier verdict stops applying. A finding's id is ``Violation.id``.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

def code_fingerprint(text: str, rubric_version: str) -> str:
    """A hash of ``text`` (line endings normalized) and the rubric version."""
    return _digest("\0".join((text.replace("\r\n", "\n"), rubric_version)))


def read_lines(path: Path, first: int, last: int) -> str:
    """Lines ``first`` through ``last`` (1-based, inclusive) of ``path``."""
    return "\n".join(path.read_text(encoding="utf-8", errors="replace").splitlines()[first - 1:last])


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
