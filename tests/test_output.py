"""Tests for slop output formatters."""

from __future__ import annotations

import json

from slop.color import set_color
from slop.models import LintResult, RuleResult, Violation
from slop.output import _plural, format_human, format_json, format_quiet


# Disable color for predictable test output
set_color(False)


def _make_result(
    violations: list[Violation] | None = None,
    rule_name: str = "complexity.cyclomatic",
    status: str = "fail",
    **kwargs,
) -> LintResult:
    """Build a minimal LintResult for testing."""
    vs = violations or []
    rr = RuleResult(
        rule=rule_name,
        status=status,
        violations=vs,
        summary={"functions_checked": 10, "violation_count": len(vs)},
    )
    return LintResult(
        version="0.1.0",
        root="/test",
        languages=["python"],
        display_root="./test",
        rule_results={rule_name: rr},
        rules_checked=1,
        violation_count=len([v for v in vs if v.severity == "error"]),
        advisory_count=len([v for v in vs if v.severity != "error"]),
        result="fail" if vs else "pass",
        **kwargs,
    )


def _violation(rule: str = "complexity.cyclomatic", file: str = "a.py", line: int = 1, symbol: str = "f", value: int = 15) -> Violation:
    return Violation(rule=rule, file=file, line=line, symbol=symbol, message=f"CCX {value} exceeds 10", severity="error", value=value, threshold=10)


# ---------------------------------------------------------------------------
# Plurals
# ---------------------------------------------------------------------------


def test_plural_singular():
    assert _plural(1, "violation") == "1 violation"


def test_plural_multiple():
    assert _plural(53, "violation") == "53 violations"


def test_plural_custom():
    assert _plural(2, "advisory", "advisories") == "2 advisories"
    assert _plural(1, "advisory", "advisories") == "1 advisory"


def test_plural_zero():
    assert _plural(0, "violation") == "0 violations"


# ---------------------------------------------------------------------------
# Human formatting
# ---------------------------------------------------------------------------


def test_human_shows_display_root():
    result = _make_result([], status="pass")
    output = format_human(result)
    assert "./test" in output


def test_human_groups_by_subrule():
    vs = [
        _violation("complexity.cyclomatic", "a.py", 1, "f1", 15),
        _violation("complexity.cognitive", "a.py", 1, "f1", 20),
    ]
    rr_cyc = RuleResult(rule="complexity.cyclomatic", status="fail", violations=[vs[0]], summary={"functions_checked": 10, "violation_count": 1})
    rr_cog = RuleResult(rule="complexity.cognitive", status="fail", violations=[vs[1]], summary={"functions_checked": 10, "violation_count": 1})
    result = LintResult(
        version="0.1.0", root="/test", languages=["python"], display_root="./test",
        rule_results={"complexity.cyclomatic": rr_cyc, "complexity.cognitive": rr_cog},
        rules_checked=2, violation_count=2, result="fail",
    )
    output = format_human(result)
    # Should have sub-rule headers
    assert "cyclomatic" in output
    assert "cognitive" in output


def test_human_caps_violations():
    vs = [_violation(value=15 - i) for i in range(10)]
    result = _make_result(vs)
    output = format_human(result, max_violations=3)
    assert "...and 7 more" in output


def test_human_clean_shows_checkmark():
    result = _make_result([], status="pass")
    output = format_human(result)
    assert "\u2713" in output  # checkmark


def test_human_skipped_shows_info():
    rr = RuleResult(rule="orphans", status="skip")
    result = LintResult(
        version="0.1.0", root="/test", languages=[], display_root="./test",
        rule_results={"orphans": rr},
        rules_checked=0, rules_skipped=1, result="pass",
    )
    output = format_human(result)
    assert "skipped" in output


# ---------------------------------------------------------------------------
# Quiet mode
# ---------------------------------------------------------------------------


def test_quiet_is_one_line():
    result = _make_result([_violation()])
    output = format_quiet(result)
    assert "\n" not in output
    assert "violation" in output
    assert "FAIL" in output


def test_quiet_pass():
    result = _make_result([], status="pass")
    output = format_quiet(result)
    assert "PASS" in output


# ---------------------------------------------------------------------------
# JSON
# ---------------------------------------------------------------------------


def test_json_is_valid():
    result = _make_result([_violation()])
    output = format_json(result)
    data = json.loads(output)
    assert "version" in data
    assert "rules" in data
    assert "summary" in data


def test_json_has_expected_keys():
    result = _make_result([_violation()])
    data = json.loads(format_json(result))
    assert data["summary"]["violation_count"] == 1
    assert data["summary"]["result"] == "fail"
    rule_data = data["rules"]["complexity.cyclomatic"]
    assert rule_data["status"] == "fail"
    assert len(rule_data["violations"]) == 1
