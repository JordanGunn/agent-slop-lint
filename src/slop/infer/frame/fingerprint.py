"""Identity and staleness for a finding.

``code_fingerprint`` changes when the code shown or the rubric changes, which is when an
earlier verdict stops applying. A finding's id is ``Violation.id``.
"""
from __future__ import annotations

import hashlib

def code_fingerprint(text: str, rubric_version: str) -> str:
    """A hash of ``text`` (line endings normalized) and the rubric version."""
    return _digest("\0".join((text.replace("\r\n", "\n"), rubric_version)))


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
