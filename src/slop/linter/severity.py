"""Severity vocabulary for rule findings.

``Severity`` is an ``IntEnum`` so members are directly comparable —
``Severity.OFF < Severity.INFO < Severity.WARNING < Severity.ERROR`` —
for filtering and ranking. Use ``.label()`` to convert a member to its
lowercase string form (``"off"``, ``"info"``, ``"warning"``, ``"error"``)
when serializing to JSON or comparing against string-typed fields on
``Slop`` / ``RuleConfig`` (those remain ``str`` for TOML round-tripping
and historic call-site shape).
"""
from __future__ import annotations

from enum import IntEnum


class Severity(IntEnum):
    """Rule-violation severity ranks."""

    OFF = 0
    INFO = 1
    WARNING = 2
    ERROR = 3

    def label(self) -> str:
        """Return a lowercase string for the given severity based on the enum member name."""
        return self.name.lower()
