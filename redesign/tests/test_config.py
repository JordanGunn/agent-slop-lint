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
