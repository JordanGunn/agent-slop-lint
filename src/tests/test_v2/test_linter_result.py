"""Tests for ``slop.linter.result.Result``."""
from __future__ import annotations

from slop.linter.result import Result


class TestResultDefaults:
    def test_minimal_construction(self):
        r = Result(version="2.0.0", root="/tmp", languages=["python"])
        assert r.version == "2.0.0"
        assert r.rule_results == {}
        assert r.slop_count == 0
        assert r.verdict == "pass"


class TestResultFormatting:
    def test_json_returns_dict(self):
        r = Result(version="x", root="/", languages=["python"], verdict="pass")
        d = r.json()
        assert isinstance(d, dict)
        assert d["version"] == "x"
        assert d["root"] == "/"
        assert d["languages"] == ["python"]
        assert "summary" in d
        assert d["summary"]["result"] == "pass"

    def test_pretty_returns_str(self):
        r = Result(version="x", root="/", languages=[], verdict="pass")
        out = r.pretty()
        assert isinstance(out, str)
        assert len(out) > 0

    def test_pretty_quiet_returns_one_line(self):
        r = Result(version="x", root="/", languages=[], verdict="pass")
        out = r.pretty(verbose=False)
        # The quiet formatter renders a single summary line.
        assert "\n" not in out.strip()
