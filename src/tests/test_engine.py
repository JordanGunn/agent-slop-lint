"""Tests for slop engine — rule orchestration and result aggregation."""

from __future__ import annotations

from pathlib import Path

from slop.config import load_config
from slop.engine import run_lint
from slop.models import RuleConfig, SlopConfig


def _config_with_rules(tmp_path: Path, **rule_overrides) -> SlopConfig:
    """Build a SlopConfig pointing at tmp_path with rule overrides."""
    # Write a trivial Python file so kernels have something to analyze
    (tmp_path / "simple.py").write_text("def add(a, b):\n    return a + b\n")
    config = load_config(root=str(tmp_path))
    for cat, overrides in rule_overrides.items():
        rc = config.rules.get(cat, RuleConfig())
        rc_params = dict(rc.params)
        rc_params.update(overrides)
        config.rules[cat] = RuleConfig(
            enabled=overrides.get("enabled", rc.enabled),
            severity=overrides.get("severity", rc.severity),
            params=rc_params,
        )
    return config


def test_engine_returns_pass_for_clean_code(tmp_path: Path):
    (tmp_path / "clean.py").write_text("x = 1\n")
    config = load_config(root=str(tmp_path))
    # Disable rules that need git or complex setup
    for cat in ("hotspots", "packages", "deps", "orphans", "class"):
        config.rules[cat] = RuleConfig(enabled=False)
    result = run_lint(config)
    assert result.result == "pass"


def test_engine_returns_fail_when_violations_exist(tmp_path: Path):
    (tmp_path / "complex.py").write_text(
        "def f(a,b,c,d,e,f,g,h,i,j,k):\n"
        + "".join(f"    if {chr(97+i)}: pass\n" for i in range(11))
    )
    config = load_config(root=str(tmp_path))
    for cat in ("hotspots", "packages", "deps", "orphans", "class"):
        config.rules[cat] = RuleConfig(enabled=False)
    result = run_lint(config)
    assert result.result == "fail"
    assert result.violation_count > 0


def test_disabled_rule_is_skipped(tmp_path: Path):
    (tmp_path / "a.py").write_text("x = 1\n")
    config = load_config(root=str(tmp_path))
    for cat in config.rules:
        config.rules[cat] = RuleConfig(enabled=False)
    result = run_lint(config)
    assert result.rules_skipped > 0
    assert result.rules_checked == 0
    assert result.result == "pass"


def test_filter_category_runs_only_that_category(tmp_path: Path):
    (tmp_path / "a.py").write_text("def f():\n    pass\n")
    config = load_config(root=str(tmp_path))
    result = run_lint(config, filter_category="complexity")
    # Only complexity rules should appear in results
    for rule_name in result.rule_results:
        assert rule_name.startswith("complexity"), f"Unexpected rule: {rule_name}"


def test_filter_rule_runs_one_rule(tmp_path: Path):
    (tmp_path / "a.py").write_text("def f():\n    pass\n")
    config = load_config(root=str(tmp_path))
    result = run_lint(config, filter_rule="complexity.cyclomatic")
    assert list(result.rule_results.keys()) == ["complexity.cyclomatic"]


def test_unknown_rule_returns_error(tmp_path: Path):
    config = load_config(root=str(tmp_path))
    result = run_lint(config, filter_rule="nonexistent.rule")
    assert result.result == "error"


def test_unknown_category_returns_error(tmp_path: Path):
    config = load_config(root=str(tmp_path))
    result = run_lint(config, filter_category="nonexistent")
    assert result.result == "error"


def test_display_root_passes_through(tmp_path: Path):
    (tmp_path / "a.py").write_text("x = 1\n")
    config = load_config(root=str(tmp_path))
    for cat in config.rules:
        config.rules[cat] = RuleConfig(enabled=False)
    result = run_lint(config, display_root="./my-project")
    assert result.display_root == "./my-project"


def test_prefix_match_runs_subcategory(tmp_path: Path):
    (tmp_path / "a.py").write_text("class Foo:\n    pass\n")
    config = load_config(root=str(tmp_path))
    result = run_lint(config, filter_rule="class.inheritance")
    rule_names = list(result.rule_results.keys())
    assert "class.inheritance.depth" in rule_names
    assert "class.inheritance.children" in rule_names
    assert "class.coupling" not in rule_names


def test_rule_with_errors_and_zero_violations_is_coerced_to_error(
    tmp_path: Path, monkeypatch
):
    """A rule that returns errors (e.g. missing binary) must not render as pass.

    Simulates the silent-failure case where a kernel bailed but the rule
    wrapper still produced pass-status with an empty violations list.
    """
    from slop import rules as rules_module
    from slop.models import RuleDefinition, RuleResult

    def fake_run(root, rule_config, slop_config):
        return RuleResult(
            rule="complexity.cyclomatic",
            status="pass",
            violations=[],
            errors=["fd not found"],
        )

    fake_def = RuleDefinition(
        name="complexity.cyclomatic",
        category="complexity",
        description="test override",
        run=fake_run,
    )
    # RULES_BY_NAME is a dict — engine looks up filter_rule via this mapping.
    monkeypatch.setitem(rules_module.RULES_BY_NAME, "complexity.cyclomatic", fake_def)

    config = load_config(root=str(tmp_path))
    result = run_lint(config, filter_rule="complexity.cyclomatic")

    rr = result.rule_results["complexity.cyclomatic"]
    assert rr.status == "error"
    assert rr.errors == ["fd not found"]
    assert result.result == "error"
