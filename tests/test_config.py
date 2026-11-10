"""Config — per-altitude thresholds validated against each rule's declared
altitudes. A threshold the rule can never apply is a load error, not a silent
drop (the structural cure for the legacy 'config keyed wrong' bug)."""
from __future__ import annotations

from pathlib import Path

import pytest

from slop.config import AnalysisConfig
from slop.finding import Severity
from slop.rules import RULE_REGISTRY


def test_defaults_are_coherent():
    cfg = AnalysisConfig.defaults(RULE_REGISTRY)
    cyclo = cfg.for_rule("complexity.cyclomatic")
    assert cyclo is not None and cyclo.enabled
    # Cyclomatic is Callable-only — the class-altitude WMC gate was dropped (it
    # conflated breadth with tangle; class size belongs to a future NOM rule).
    assert cyclo.thresholds == {"callable": 10}
    assert cyclo.severity is Severity.ERROR


def test_load_with_no_toml_returns_defaults(tmp_path: Path):
    cfg = AnalysisConfig.load(tmp_path, RULE_REGISTRY)
    assert cfg.for_rule("vocabulary").param("package_min_distinct") == 40


def test_toml_override_applies(tmp_path: Path):
    (tmp_path / ".slop.toml").write_text(
        '[rules."complexity.cyclomatic"]\n'
        'severity = "warning"\n'
        '[rules."complexity.cyclomatic".thresholds]\n'
        'callable = 15\n'
    )
    cfg = AnalysisConfig.load(tmp_path, RULE_REGISTRY)
    cyclo = cfg.for_rule("complexity.cyclomatic")
    assert cyclo.severity is Severity.WARNING
    assert cyclo.thresholds["callable"] == 15


def test_threshold_for_undeclared_altitude_is_a_load_error(tmp_path: Path):
    # cyclomatic is defined at {callable, class}; 'module' is not a valid altitude.
    (tmp_path / ".slop.toml").write_text(
        '[rules."complexity.cyclomatic".thresholds]\n'
        'module = 5\n'
    )
    with pytest.raises(ValueError, match="not a declared altitude"):
        AnalysisConfig.load(tmp_path, RULE_REGISTRY)


def test_unknown_rule_in_toml_is_an_error(tmp_path: Path):
    (tmp_path / ".slop.toml").write_text('[rules."does.not.exist"]\nenabled = false\n')
    with pytest.raises(ValueError, match="unknown rule"):
        AnalysisConfig.load(tmp_path, RULE_REGISTRY)


# ---- exclude --------------------------------------------------------------------------

def test_exclusion_globs_are_relative_to_the_config_directory(tmp_path: Path):
    from slop.config import Exclusion
    ex = Exclusion(("tests/**", "**/vendor/**", "gen_*.py"), tmp_path.resolve())
    assert ex.excludes(tmp_path / "tests" / "unit" / "test_a.py")
    assert ex.excludes(tmp_path / "vendor" / "x.py")           # leading **/ reaches the top level
    assert ex.excludes(tmp_path / "pkg" / "vendor" / "x.py")
    assert ex.excludes(tmp_path / "gen_a.py")
    assert not ex.excludes(tmp_path / "src" / "tests_helper.py")
    assert not ex.excludes(tmp_path.parent / "tests" / "x.py")  # outside the config directory


def test_exclude_must_be_a_list_of_strings(tmp_path: Path):
    (tmp_path / ".slop.toml").write_text('exclude = "tests/**"\n')
    with pytest.raises(ValueError, match="exclude"):
        AnalysisConfig.scan(tmp_path, RULE_REGISTRY)


# ---- rule params ----------------------------------------------------------------------

def test_params_table_overrides_a_declared_param(tmp_path: Path):
    # `slop init` writes params.<name>; it must reach the rule, not nest under "params".
    (tmp_path / ".slop.toml").write_text('[rules."class-shape"]\nparams.cbo_attention = 0\n')
    rc = AnalysisConfig.load(tmp_path, RULE_REGISTRY).for_rule("class-shape")
    assert rc.param("cbo_attention") == 0
    assert "params" not in rc.params
    assert rc.param("dit_attention") == 4          # untouched defaults survive


def test_an_unknown_param_is_a_load_error_not_a_silent_no_op(tmp_path: Path):
    (tmp_path / ".slop.toml").write_text('[rules."class-shape"]\nparams.cbo_attenshun = 0\n')
    with pytest.raises(ValueError, match="cbo_attenshun.*can never read"):
        AnalysisConfig.load(tmp_path, RULE_REGISTRY)


def test_a_param_outside_the_params_table_is_a_load_error(tmp_path: Path):
    (tmp_path / ".slop.toml").write_text('[rules."class-shape"]\ncbo_attention = 0\n')
    with pytest.raises(ValueError, match="go in a 'params' table"):
        AnalysisConfig.load(tmp_path, RULE_REGISTRY)


def test_the_init_template_loads_as_written(tmp_path: Path):
    # Uncommenting every generated line must give exactly the defaults, not an error.
    from slop import cli
    cli.init(tmp_path)
    text = (tmp_path / ".slop.toml").read_text()
    (tmp_path / ".slop.toml").write_text("\n".join(
        ln[2:] if ln.startswith("# ") and "=" in ln or ln.startswith("# [") else ln
        for ln in text.splitlines()))
    loaded = AnalysisConfig.load(tmp_path, RULE_REGISTRY)
    assert {n: (c.thresholds, c.params) for n, c in loaded.rules.items()} == \
           {n: (c.thresholds, c.params) for n, c in AnalysisConfig.defaults(RULE_REGISTRY).rules.items()}
