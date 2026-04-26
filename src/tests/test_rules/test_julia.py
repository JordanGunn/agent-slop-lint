"""Smoke tests for Julia language support across structural rules.

Each test writes a small `.jl` fixture and runs the rule with
``languages=['julia']``. Goal: confirm Julia files parse, the kernel
walks them, and the rule wrapper produces a Violation in the expected
shape. Threshold-tuning correctness is exercised by the per-rule tests
on Python; here we only check the language plumbing.
"""

from __future__ import annotations

from pathlib import Path

from slop.models import RuleConfig, SlopConfig
from slop.rules.complexity import run_cyclomatic
from slop.rules.dependencies import run_cycles
from slop.rules.halstead import run_volume
from slop.rules.npath import run_npath


_BRANCHY_JL = """\
function branchy(x)
    if x > 0
        if x > 10
            return "big"
        elseif x > 5
            return "med"
        else
            return "small"
        end
    elseif x < 0
        for i in 1:abs(x)
            if i == 5
                continue
            end
        end
        return "neg"
    else
        return "zero"
    end
end
"""


def _slop_config() -> SlopConfig:
    return SlopConfig(rules={}, languages=["julia"])


def _rule_config(**overrides) -> RuleConfig:
    return RuleConfig(enabled=True, severity="error", params=overrides)


def test_julia_cyclomatic_flags_branchy_function(tmp_path: Path):
    (tmp_path / "branchy.jl").write_text(_BRANCHY_JL)
    cfg = _rule_config(cyclomatic_threshold=5)
    result = run_cyclomatic(tmp_path, cfg, _slop_config())
    assert result.status == "fail", result.summary
    assert any(v.symbol == "branchy" for v in result.violations)


def test_julia_npath_runs_without_error(tmp_path: Path):
    (tmp_path / "branchy.jl").write_text(_BRANCHY_JL)
    cfg = _rule_config(npath_threshold=200)
    result = run_npath(tmp_path, cfg, _slop_config())
    # NPath under-counts nested branches in flat-body langs (documented
    # limitation in docs/JULIA.md). We only check it runs and analyses
    # the function.
    assert result.status in ("pass", "fail")
    assert result.summary.get("functions_checked", 0) >= 1


def test_julia_halstead_runs_without_error(tmp_path: Path):
    (tmp_path / "branchy.jl").write_text(_BRANCHY_JL)
    cfg = _rule_config(volume_threshold=10000)
    result = run_volume(tmp_path, cfg, _slop_config())
    assert result.status == "pass"
    assert result.summary.get("functions_checked", 0) >= 1


def test_julia_deps_runs_without_error(tmp_path: Path):
    (tmp_path / "mod.jl").write_text(
        "using LinearAlgebra\n"
        "import Base: show\n"
        "using Foo.Bar\n"
        "import Other\n"
        "function f(x); x + 1; end\n"
    )
    cfg = _rule_config()
    result = run_cycles(tmp_path, cfg, _slop_config())
    # Cycle detection on a single file with external-only imports should
    # not flag anything. We just verify the rule plumbed Julia files.
    assert result.status == "pass"
