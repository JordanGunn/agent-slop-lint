"""Tests for slop halstead rules."""

from __future__ import annotations

from pathlib import Path

from slop.models import RuleConfig, SlopConfig
from slop.rules.halstead import run_difficulty, run_volume

_TRIVIAL = "def add(a, b):\n    return a + b\n"

# Dense function with many unique operators and repeated operands.
# Intended to blow past the test thresholds on both Volume and Difficulty.
_DENSE = """\
def transform(a, b, c, d, e, f, g, h, i, j):
    x = a + b * c - d / e
    y = f % g + h * i - j
    z = a + b + c + d + e + f + g + h + i + j
    w = (a * b) + (c * d) + (e * f) + (g * h) + (i * j)
    v = a and b or c and d or e and f or g and h or i and j
    u = a == b or c != d or e < f or g > h or i <= j
    t = not a and not b and not c and not d and not e
    s = (a + b + c + d) * (e + f + g + h) / (i + j + 1)
    r = a | b | c | d | e | f | g | h | i | j
    return x + y + z + w + v + u + t + s + r
"""


def _write_file(tmp_path: Path, source: str, name: str = "sample.py") -> Path:
    f = tmp_path / name
    f.write_text(source)
    return tmp_path


def _slop_config() -> SlopConfig:
    return SlopConfig(rules={})


def _rule_config(**overrides) -> RuleConfig:
    defaults = {"threshold": 1500}
    defaults.update(overrides)
    return RuleConfig(enabled=True, severity="error", params=defaults)


def test_volume_passes_on_trivial_function(tmp_path: Path) -> None:
    root = _write_file(tmp_path, _TRIVIAL)
    result = run_volume(root, _rule_config(), _slop_config())
    assert result.status == "pass"
    assert result.violations == []
    assert result.summary["functions_checked"] >= 1


def test_difficulty_passes_on_trivial_function(tmp_path: Path) -> None:
    root = _write_file(tmp_path, _TRIVIAL)
    result = run_difficulty(root, _rule_config(), _slop_config())
    assert result.status == "pass"
    assert result.violations == []


def test_volume_flags_dense_function(tmp_path: Path) -> None:
    # Lower threshold so the dense fixture reliably trips it.
    root = _write_file(tmp_path, _DENSE)
    result = run_volume(root, _rule_config(threshold=50), _slop_config())
    assert result.status == "fail"
    assert any(v.symbol == "transform" for v in result.violations)
    flagged = next(v for v in result.violations if v.symbol == "transform")
    assert flagged.value is not None and flagged.value > 50
    assert flagged.rule == "information.volume"


def test_difficulty_flags_dense_function(tmp_path: Path) -> None:
    root = _write_file(tmp_path, _DENSE)
    result = run_difficulty(root, _rule_config(threshold=1), _slop_config())
    assert result.status == "fail"
    assert any(v.symbol == "transform" for v in result.violations)
    flagged = next(v for v in result.violations if v.symbol == "transform")
    assert flagged.value is not None and flagged.value > 1
    assert flagged.rule == "information.difficulty"


def test_volume_respects_custom_threshold(tmp_path: Path) -> None:
    root = _write_file(tmp_path, _TRIVIAL)
    # Pathologically low threshold: every function should fail.
    result = run_volume(root, _rule_config(threshold=0), _slop_config())
    assert result.status == "fail"
    assert len(result.violations) >= 1



# ---------------------------------------------------------------------------
# token_weight_alpha refinement
# ---------------------------------------------------------------------------

# Function with single-letter identifiers — terse naming
