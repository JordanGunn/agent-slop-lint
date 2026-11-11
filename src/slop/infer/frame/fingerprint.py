"""Identity and staleness for a finding.

``finding_id`` names a finding so it survives edits that move it: it keys on the rule, the
file and the subject, not the line. ``code_fingerprint`` changes when the code shown or the
rubric changes, which is when an earlier verdict stops applying.
"""
from __future__ import annotations

import hashlib

_ID_LENGTH = 16


def finding_id(rule: str, path: str, subject: str) -> str:
    """A stable id for the finding of ``rule`` about ``subject`` in ``path``."""
    return _digest("\0".join((rule, path, subject)))[:_ID_LENGTH]


def code_fingerprint(text: str, rubric_version: str) -> str:
    """A hash of ``text`` (line endings normalized) and the rubric version."""
    return _digest("\0".join((text.replace("\r\n", "\n"), rubric_version)))


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
