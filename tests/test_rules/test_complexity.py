"""Tests for slop complexity rules."""

from __future__ import annotations

from pathlib import Path

from slop.models import RuleConfig, SlopConfig
from slop.rules.complexity import run_cognitive, run_cyclomatic

# Python source with known complexity values
_SIMPLE = "def add(a, b):\n    return a + b\n"  # ccx=1, cog=0

_MODERATE = """\
def classify(x):
    if x < 0:
        return "negative"
    elif x == 0:
        return "zero"
    elif x < 10:
        return "small"
    elif x < 100:
        return "medium"
    elif x < 1000:
        return "large"
    else:
        return "huge"
"""  # ccx=6

_COMPLEX = """\
def branchy(a, b, c, d, e, f, g, h, i, j, k):
    if a: pass
    if b: pass
    if c: pass
    if d: pass
    if e: pass
    if f: pass
    if g: pass
    if h: pass
    if i: pass
    if j: pass
    if k: pass
"""  # ccx=12


def _write_file(tmp_path: Path, source: str, name: str = "test.py") -> Path:
    f = tmp_path / name
    f.write_text(source)
    return tmp_path


def _default_config() -> SlopConfig:
    return SlopConfig(rules={})


def _rule_config(**overrides) -> RuleConfig:
    defaults = {"cyclomatic_threshold": 10, "cognitive_threshold": 15}
    defaults.update(overrides)
    return RuleConfig(enabled=True, severity="error", params=defaults)


# ---------------------------------------------------------------------------
# Cyclomatic complexity
# ---------------------------------------------------------------------------


def test_cyclomatic_pass_when_below_threshold(tmp_path: Path):
    _write_file(tmp_path, _SIMPLE)
    result = run_cyclomatic(tmp_path, _rule_config(), _default_config())
    assert result.status == "pass"
    assert result.violations == []


def test_cyclomatic_fail_when_above_threshold(tmp_path: Path):
    _write_file(tmp_path, _COMPLEX)
    result = run_cyclomatic(tmp_path, _rule_config(cyclomatic_threshold=10), _default_config())
    assert result.status == "fail"
    assert len(result.violations) == 1
    v = result.violations[0]
    assert v.rule == "complexity.cyclomatic"
    assert v.value is not None and v.value > 10
    assert v.symbol == "branchy"


def test_cyclomatic_threshold_is_configurable(tmp_path: Path):
    _write_file(tmp_path, _MODERATE)
    # threshold=5 → ccx=6 should fail
    result = run_cyclomatic(tmp_path, _rule_config(cyclomatic_threshold=5), _default_config())
    assert result.status == "fail"
    # threshold=10 → ccx=6 should pass
    result = run_cyclomatic(tmp_path, _rule_config(cyclomatic_threshold=10), _default_config())
    assert result.status == "pass"


def test_cyclomatic_violation_has_correct_fields(tmp_path: Path):
    _write_file(tmp_path, _COMPLEX)
    result = run_cyclomatic(tmp_path, _rule_config(cyclomatic_threshold=10), _default_config())
    v = result.violations[0]
    assert v.file is not None
    assert v.line is not None and v.line > 0
    assert v.severity == "error"
    assert v.threshold == 10
    assert "zone" in v.metadata


def test_cyclomatic_summary_includes_function_count(tmp_path: Path):
    _write_file(tmp_path, _SIMPLE + "\n" + _MODERATE)
    result = run_cyclomatic(tmp_path, _rule_config(), _default_config())
    assert result.summary["functions_checked"] >= 2


# ---------------------------------------------------------------------------
# Cognitive complexity
# ---------------------------------------------------------------------------


_NESTED = """\
def deeply_nested(a, b, c):
    if a:
        if b:
            if c:
                return 1
    return 0
"""  # cog is high due to nesting (1+0 + 1+1 + 1+2 = 6)


def test_cognitive_pass_when_below_threshold(tmp_path: Path):
    _write_file(tmp_path, _SIMPLE)
    result = run_cognitive(tmp_path, _rule_config(), _default_config())
    assert result.status == "pass"


def test_cognitive_fail_when_above_threshold(tmp_path: Path):
    _write_file(tmp_path, _NESTED)
    result = run_cognitive(tmp_path, _rule_config(cognitive_threshold=3), _default_config())
    assert result.status == "fail"
    assert len(result.violations) >= 1
    assert result.violations[0].rule == "complexity.cognitive"


def test_cognitive_threshold_configurable(tmp_path: Path):
    _write_file(tmp_path, _NESTED)
    # threshold=100 → should pass
    result = run_cognitive(tmp_path, _rule_config(cognitive_threshold=100), _default_config())
    assert result.status == "pass"
