"""Tests for ``slop.linter.slop.Slop`` — the finding carrier."""
from __future__ import annotations

from slop.linter.slop import Slop


class TestSlopConstruction:
    def test_minimal_construction(self):
        s = Slop(rule="lex.x", file="m.py")
        assert s.rule == "lex.x"
        assert s.file == "m.py"
        assert s.severity == "error"  # default
        assert s.metadata == {}       # default factory

    def test_suggestion_field_default_none(self):
        s = Slop(rule="r", file="f")
        assert s.suggestion is None

    def test_attribute_names_match_violation_for_duck_typing(self):
        # The migration relies on Slop having the same attribute names as
        # the legacy Slop so formatters can iterate
        # mixed lists transparently.
        s = Slop(rule="r", file="f", line=1, symbol="x", message="m",
                 severity="warning", value=5, threshold=3, metadata={"k": "v"})
        for attr in ("rule", "file", "line", "symbol", "message",
                     "severity", "value", "threshold", "metadata"):
            assert hasattr(s, attr)
