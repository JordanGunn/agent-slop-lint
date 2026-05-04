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
_TERSE = """\
def f(a, b, c, d, e):
    x = a + b
    y = c * d
    return x + y + e
"""


def test_volume_alpha_zero_behaves_identically_to_baseline(tmp_path: Path) -> None:
    """token_weight_alpha=0 must produce identical violations to the baseline."""
    root = _write_file(tmp_path, _DENSE)
    baseline = run_volume(root, _rule_config(threshold=50), _slop_config())
    with_alpha = run_volume(
        root, _rule_config(threshold=50, token_weight_alpha=0.0), _slop_config()
    )
    assert baseline.status == with_alpha.status
    assert len(baseline.violations) == len(with_alpha.violations)


def test_volume_alpha_positive_raises_adjusted_volume_for_terse_code(
    tmp_path: Path,
) -> None:
    """With alpha > 0 and terse names, adjusted volume must exceed raw volume."""
    root = _write_file(tmp_path, _TERSE)
    # Baseline: use a threshold high enough that raw volume passes
    baseline = run_volume(root, _rule_config(threshold=9999), _slop_config())
    assert baseline.status == "pass"

    # Now get the raw volume for the function
    baseline_with_low = run_volume(root, _rule_config(threshold=0), _slop_config())
    assert baseline_with_low.violations, "fixture must produce a measurable volume"
    raw_vol = baseline_with_low.violations[0].metadata["raw_volume"]

    # With alpha=1.0 and all-single-char identifiers (mean≈1.0), penalty ≈ 2.0
    # → adjusted_volume ≈ 2 * raw_volume.  Use a threshold between raw and adjusted.
    mid_threshold = raw_vol * 1.5
    result = run_volume(
        root, _rule_config(threshold=mid_threshold, token_weight_alpha=1.0), _slop_config()
    )
    # Should now fail because adjusted > mid_threshold
    assert result.status == "fail", (
        f"expected fail with alpha=1.0 and threshold={mid_threshold:.1f}, "
        f"raw_vol={raw_vol:.1f}"
    )


def test_volume_alpha_no_penalty_for_rich_names(tmp_path: Path) -> None:
    """Rich multi-word names should produce penalty ≈ 1.0 (no effective change)."""
    src = (
        "def compute_total_output_value(input_collection, scale_factor):\n"
        "    result_value = sum(input_collection) * scale_factor\n"
        "    return result_value\n"
    )
    root = _write_file(tmp_path, src)
    result = run_volume(
        root, _rule_config(threshold=0, token_weight_alpha=1.0), _slop_config()
    )
    # Metadata penalty should be close to 1.0 for richly-named function
    if result.violations:
        penalty = result.violations[0].metadata.get("penalty", 1.0)
        # `sum` is a single-token builtin that slightly depresses mean_tokens;
        # penalty < 1.3 confirms the function is not being heavily penalised.
        assert penalty < 1.3, f"expected low penalty for rich names, got {penalty}"


def test_volume_summary_includes_alpha(tmp_path: Path) -> None:
    root = _write_file(tmp_path, _TRIVIAL)
    result = run_volume(
        root, _rule_config(token_weight_alpha=0.25), _slop_config()
    )
    assert result.summary["token_weight_alpha"] == 0.25
