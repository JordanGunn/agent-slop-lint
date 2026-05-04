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
    rule_name: str = "structural.complexity.cyclomatic",
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


def _violation(rule: str = "structural.complexity.cyclomatic", file: str = "a.py", line: int = 1, symbol: str = "f", value: int = 15) -> Violation:
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
        _violation("structural.complexity.cyclomatic", "a.py", 1, "f1", 15),
        _violation("structural.complexity.cognitive", "a.py", 1, "f1", 20),
    ]
    rr_cyc = RuleResult(rule="structural.complexity.cyclomatic", status="fail", violations=[vs[0]], summary={"functions_checked": 10, "violation_count": 1})
    rr_cog = RuleResult(rule="structural.complexity.cognitive", status="fail", violations=[vs[1]], summary={"functions_checked": 10, "violation_count": 1})
    result = LintResult(
        version="0.1.0", root="/test", languages=["python"], display_root="./test",
        rule_results={"structural.complexity.cyclomatic": rr_cyc, "structural.complexity.cognitive": rr_cog},
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


def test_human_zero_files_analyzed_shows_warning_not_clean():
    """A rule that passed with zero files scanned should render as a warning,
    not a green checkmark. Counts of 0 previously hid in the ✓ clean path."""
    rr = RuleResult(
        rule="structural.complexity.cyclomatic",
        status="pass",
        violations=[],
        summary={"functions_checked": 0, "violation_count": 0},
    )
    result = LintResult(
        version="0.1.0", root="/test", languages=["python"], display_root="./test",
        rule_results={"structural.complexity.cyclomatic": rr},
        rules_checked=1, result="pass",
    )
    output = format_human(result)
    assert "no files matched" in output
    assert "\u2713 clean" not in output


def test_human_surfaces_rule_errors():
    """Errors captured on RuleResult must appear in human output, not just JSON."""
    rr = RuleResult(
        rule="structural.complexity.cyclomatic",
        status="error",
        violations=[],
        summary={"functions_checked": 0, "violation_count": 0},
        errors=["fd not found. Install from https://github.com/sharkdp/fd"],
    )
    result = LintResult(
        version="0.1.0", root="/test", languages=["python"], display_root="./test",
        rule_results={"structural.complexity.cyclomatic": rr},
        rules_checked=1, result="error",
    )
    output = format_human(result)
    assert "fd not found" in output
    assert "ERROR" in output


def test_human_error_status_does_not_render_as_clean():
    """A category whose only rule errored should not show ✓ clean."""
    rr = RuleResult(
        rule="structural.complexity.cyclomatic",
        status="error",
        violations=[],
        errors=["boom"],
    )
    result = LintResult(
        version="0.1.0", root="/test", languages=[], display_root="./test",
        rule_results={"structural.complexity.cyclomatic": rr},
        rules_checked=1, result="error",
    )
    output = format_human(result)
    assert "\u2713 clean" not in output
    assert "no files matched" not in output  # errors take precedence over zero-files


def test_human_renders_waived_findings_without_failure():
    waived = _violation("npath", "src/parser/grammar.py", 12, "parse_expr", 914)
    waived.metadata["waiver"] = {
        "id": "parser-npath",
        "reason": "Parser branch shape mirrors grammar alternatives.",
        "allow_up_to": 1200,
        "expires": "2099-01-01",
    }
    rr = RuleResult(
        rule="npath",
        status="pass",
        violations=[],
        waived_violations=[waived],
        summary={"functions_checked": 1, "violation_count": 0, "waived_count": 1},
    )
    result = LintResult(
        version="0.1.0",
        root="/test",
        languages=["python"],
        display_root="./test",
        rule_results={"npath": rr},
        rules_checked=1,
        waived_count=1,
        result="pass",
    )
    output = format_human(result)
    assert "waived by parser-npath" in output
    assert "Parser branch shape" in output
    assert "1 waived" in output
    assert "PASS" in output


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


def test_quiet_includes_waived_count():
    result = _make_result([], status="pass", waived_count=2)
    output = format_quiet(result)
    assert "2 waived" in output
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
    rule_data = data["rules"]["structural.complexity.cyclomatic"]
    assert rule_data["status"] == "fail"
    assert len(rule_data["violations"]) == 1
    assert "waived_violations" in rule_data


def test_json_includes_waived_findings():
    waived = _violation("npath", "src/parser/grammar.py", 12, "parse_expr", 914)
    waived.metadata["waiver"] = {
        "id": "parser-npath",
        "reason": "Parser branch shape mirrors grammar alternatives.",
    }
    rr = RuleResult(
        rule="npath",
        status="pass",
        waived_violations=[waived],
        summary={"functions_checked": 1, "waived_count": 1},
    )
    result = LintResult(
        version="0.1.0",
        root="/test",
        languages=["python"],
        rule_results={"npath": rr},
        rules_checked=1,
        waived_count=1,
        result="pass",
    )
    data = json.loads(format_json(result))
    assert data["summary"]["waived_count"] == 1
    waiver = data["rules"]["npath"]["waived_violations"][0]["metadata"]["waiver"]
    assert waiver["id"] == "parser-npath"
