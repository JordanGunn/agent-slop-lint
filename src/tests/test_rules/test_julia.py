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
    cfg = _rule_config(threshold=10000)
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


# ---------------------------------------------------------------------------
# Function-shape detection (v0.7.1 hotfix)
# ---------------------------------------------------------------------------


def test_julia_cyclomatic_detects_short_form_function(tmp_path: Path):
    """`f(x) = expr` short-form functions are detected and named."""
    (tmp_path / "shortform.jl").write_text(
        'branchy(x) = x > 0 ? (x > 10 ? "big" : "small") : "neg"\n'
    )
    cfg = _rule_config(cyclomatic_threshold=2)
    result = run_cyclomatic(tmp_path, cfg, _slop_config())
    assert result.status == "fail", result.summary
    assert any(v.symbol == "branchy" for v in result.violations)


def test_julia_cyclomatic_detects_operator_method(tmp_path: Path):
    """`+(a, b) = ...` operator-method definitions name themselves correctly."""
    (tmp_path / "op.jl").write_text(
        "-(a::Int, b::Int) = a > b ? a : b\n"
    )
    cfg = _rule_config(cyclomatic_threshold=1)
    result = run_cyclomatic(tmp_path, cfg, _slop_config())
    assert result.status == "fail"
    assert any(v.symbol == "-" for v in result.violations)


def test_julia_cyclomatic_detects_do_block(tmp_path: Path):
    """`map(xs) do x ... end` do-blocks count as anonymous functions."""
    (tmp_path / "do.jl").write_text(
        "result = map([1,2,3]) do x\n"
        "    if x > 1\n"
        "        x * 2\n"
        "    else\n"
        "        x\n"
        "    end\n"
        "end\n"
    )
    cfg = _rule_config(cyclomatic_threshold=1)
    result = run_cyclomatic(tmp_path, cfg, _slop_config())
    assert result.status == "fail"
    # do-blocks are anonymous; name is "<lambda>"
    assert any(v.symbol == "<lambda>" for v in result.violations)


def test_julia_cyclomatic_detects_dotted_method_name(tmp_path: Path):
    """`function Base.show(...)` extracts the method name (`show`), not '<anonymous>'."""
    (tmp_path / "dotted.jl").write_text(
        "function Base.show(io::IO, x::Float64)\n"
        "    if x > 0\n"
        "        print(io, x)\n"
        "    else\n"
        "        print(io, -x)\n"
        "    end\n"
        "end\n"
    )
    cfg = _rule_config(cyclomatic_threshold=1)
    result = run_cyclomatic(tmp_path, cfg, _slop_config())
    assert result.status == "fail"
    assert any(v.symbol == "show" for v in result.violations), [v.symbol for v in result.violations]


def test_julia_cyclomatic_detects_where_clause_function(tmp_path: Path):
    """`function f(x) where T ... end` extracts the function name through the where_expression."""
    (tmp_path / "where.jl").write_text(
        "function f(x::T) where T\n"
        "    if x > 0\n"
        "        x\n"
        "    else\n"
        "        -x\n"
        "    end\n"
        "end\n"
    )
    cfg = _rule_config(cyclomatic_threshold=1)
    result = run_cyclomatic(tmp_path, cfg, _slop_config())
    assert result.status == "fail"
    assert any(v.symbol == "f" for v in result.violations), [v.symbol for v in result.violations]


def test_julia_assignment_is_not_treated_as_function(tmp_path: Path):
    """Plain variable assignments (`x = 1`, `y = some_func()`) must not be detected as functions.

    Guards the LHS-is-call_expression check in `_julia_is_function_node`.
    """
    (tmp_path / "vars.jl").write_text(
        "x = 42\n"
        "y = some_func()\n"
        "z = [1, 2, 3]\n"
    )
    cfg = _rule_config(cyclomatic_threshold=1)
    result = run_cyclomatic(tmp_path, cfg, _slop_config())
    # No functions in the file means: no violations, regardless of threshold.
    assert result.status == "pass", result.summary
    assert result.violations == []
    assert result.summary.get("functions_checked", 0) == 0
