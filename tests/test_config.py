"""Config: per-altitude thresholds validated against each rule's declared altitudes.
A key the rule can never apply is a load error, not a silent drop."""
from __future__ import annotations

from pathlib import Path

import pytest

from slop.config import AnalysisConfig, Exclusion
from slop.rules import RULE_REGISTRY
from slop.scope import scan_corpus


def _write(root: Path, text: str) -> None:
    (root / ".slop.toml").write_text(text)


def test_defaults_are_coherent():
    cfg = AnalysisConfig.defaults(RULE_REGISTRY)
    cyclo = cfg.for_rule("complexity.cyclomatic")
    assert cyclo is not None and cyclo.enabled
    assert cyclo.thresholds == {"callable": 10}
    assert set(cfg.rules) == {r.name for r in RULE_REGISTRY}


def test_cohesion_is_the_only_rule_off_by_default():
    cfg = AnalysisConfig.defaults(RULE_REGISTRY)
    assert {n for n, rc in cfg.rules.items() if not rc.enabled} == {"class.cohesion"}


def test_load_with_no_toml_returns_defaults(tmp_path: Path):
    cfg = AnalysisConfig.load(tmp_path, RULE_REGISTRY)
    assert cfg.rules == AnalysisConfig.defaults(RULE_REGISTRY).rules
    assert cfg.languages == frozenset()
    assert not cfg.exclusion.patterns


def test_toml_threshold_override_applies_and_leaves_other_rules(tmp_path: Path):
    _write(tmp_path, '[rules."complexity.cyclomatic".thresholds]\ncallable = 15\n')
    cfg = AnalysisConfig.load(tmp_path, RULE_REGISTRY)
    assert cfg.for_rule("complexity.cyclomatic").thresholds["callable"] == 15
    assert cfg.for_rule("complexity.cognitive").thresholds == {"callable": 15}  # its own default


def test_a_rule_can_be_disabled_and_a_default_off_rule_enabled(tmp_path: Path):
    _write(tmp_path,
           '[rules."complexity.cyclomatic"]\nenabled = false\n'
           '[rules."class.cohesion"]\nenabled = true\n')
    cfg = AnalysisConfig.load(tmp_path, RULE_REGISTRY)
    assert not cfg.for_rule("complexity.cyclomatic").enabled
    assert cfg.for_rule("class.cohesion").enabled


def test_threshold_for_undeclared_altitude_is_a_load_error(tmp_path: Path):
    _write(tmp_path, '[rules."complexity.cyclomatic".thresholds]\nmodule = 5\n')
    with pytest.raises(ValueError, match="not a declared altitude"):
        AnalysisConfig.load(tmp_path, RULE_REGISTRY)


def test_unknown_rule_in_toml_is_an_error(tmp_path: Path):
    _write(tmp_path, '[rules."does.not.exist"]\nenabled = false\n')
    with pytest.raises(ValueError, match="unknown rule"):
        AnalysisConfig.load(tmp_path, RULE_REGISTRY)


def test_a_family_name_is_not_a_rule(tmp_path: Path):
    _write(tmp_path, '[rules.complexity]\nenabled = false\n')
    with pytest.raises(ValueError, match="unknown rule 'complexity'"):
        AnalysisConfig.load(tmp_path, RULE_REGISTRY)


def test_severity_is_no_longer_a_rule_key(tmp_path: Path):
    _write(tmp_path, '[rules."complexity.cyclomatic"]\nseverity = "warning"\n')
    with pytest.raises(ValueError, match="severity"):
        AnalysisConfig.load(tmp_path, RULE_REGISTRY)


def test_a_bare_key_in_a_rule_table_is_rejected(tmp_path: Path):
    _write(tmp_path, '[rules."complexity.cyclomatic"]\ncallable = 3\n')
    with pytest.raises(ValueError, match="unknown key"):
        AnalysisConfig.load(tmp_path, RULE_REGISTRY)


# ---- top-level keys -------------------------------------------------------------------

def test_an_unknown_top_level_key_is_rejected_by_load(tmp_path: Path):
    _write(tmp_path, '[ignore]\nfunctions = ["f"]\n')
    with pytest.raises(ValueError, match="unknown key.*ignore"):
        AnalysisConfig.load(tmp_path, RULE_REGISTRY)


def test_read_only_commands_do_not_read_rules_or_unknown_keys(tmp_path: Path):
    # `scan` serves the commands that never check rules, so a stale config cannot block them,
    # yet its exclude and languages still apply.
    _write(tmp_path, 'exclude = ["gen/**"]\nlanguages = ["python"]\n'
                     '[ignore]\nx = 1\n[rules.gone]\nenabled = true\n')
    cfg = AnalysisConfig.scan(tmp_path, RULE_REGISTRY)
    assert cfg.exclusion.patterns == ("gen/**",)
    assert cfg.languages == frozenset({"python"})
    assert cfg.rules == AnalysisConfig.defaults(RULE_REGISTRY).rules


# ---- exclude --------------------------------------------------------------------------

def test_exclusion_globs_are_relative_to_the_config_directory(tmp_path: Path):
    ex = Exclusion(("tests/**", "**/vendor/**", "gen_*.py"), tmp_path.resolve())
    assert ex.excludes(tmp_path / "tests" / "unit" / "test_a.py")
    assert ex.excludes(tmp_path / "vendor" / "x.py")           # leading **/ reaches the top level
    assert ex.excludes(tmp_path / "pkg" / "vendor" / "x.py")
    assert ex.excludes(tmp_path / "gen_a.py")
    assert not ex.excludes(tmp_path / "src" / "tests_helper.py")
    assert not ex.excludes(tmp_path.parent / "tests" / "x.py")  # outside the config directory


@pytest.mark.parametrize("loader", [AnalysisConfig.scan, AnalysisConfig.load])
def test_exclude_must_be_a_list_of_strings(tmp_path: Path, loader):
    _write(tmp_path, 'exclude = "tests/**"\n')
    with pytest.raises(ValueError, match="exclude"):
        loader(tmp_path, RULE_REGISTRY)


def test_exclude_removes_files_from_the_corpus(tmp_path: Path):
    (tmp_path / "app.py").write_text("x = 1\n")
    (tmp_path / "skip").mkdir()
    (tmp_path / "skip" / "m.py").write_text("y = 1\n")
    def modules(config) -> set[str]:
        corpus = scan_corpus(tmp_path, config)
        return {m.qualname for r in corpus.realms() for p in r.packages() for m in p.modules()}

    everything = modules(None)
    assert len(everything) == 2
    _write(tmp_path, 'exclude = ["skip/**"]\n')
    kept = modules(AnalysisConfig.load(tmp_path, RULE_REGISTRY))
    assert len(kept) == 1 and kept < everything


# ---- languages ------------------------------------------------------------------------

@pytest.mark.parametrize("loader", [AnalysisConfig.scan, AnalysisConfig.load])
def test_an_unknown_language_is_an_error(tmp_path: Path, loader):
    _write(tmp_path, 'languages = ["pyhton"]\n')
    with pytest.raises(ValueError, match="unknown language.*pyhton"):
        loader(tmp_path, RULE_REGISTRY)


def test_languages_must_be_a_list(tmp_path: Path):
    _write(tmp_path, 'languages = "python"\n')
    with pytest.raises(ValueError, match="languages"):
        AnalysisConfig.load(tmp_path, RULE_REGISTRY)


# ---- rule params ----------------------------------------------------------------------

def test_params_table_overrides_a_declared_param(tmp_path: Path):
    # `slop init` writes params.<name>; it must reach the rule, not nest under "params".
    _write(tmp_path, '[rules."structure.duplication"]\nparams.min_leaf_nodes = 3\n')
    rc = AnalysisConfig.load(tmp_path, RULE_REGISTRY).for_rule("structure.duplication")
    assert rc.param("min_leaf_nodes") == 3
    assert "params" not in rc.params


def test_params_in_a_nested_table_are_equivalent(tmp_path: Path):
    _write(tmp_path, '[rules."structure.duplication".params]\nmin_leaf_nodes = 4\n')
    rc = AnalysisConfig.load(tmp_path, RULE_REGISTRY).for_rule("structure.duplication")
    assert rc.param("min_leaf_nodes") == 4


def test_an_unknown_param_is_a_load_error_not_a_silent_no_op(tmp_path: Path):
    _write(tmp_path, '[rules."structure.duplication"]\nparams.min_leaf_nodez = 3\n')
    with pytest.raises(ValueError, match="min_leaf_nodez.*can never read"):
        AnalysisConfig.load(tmp_path, RULE_REGISTRY)


def test_params_must_be_a_table(tmp_path: Path):
    _write(tmp_path, '[rules."structure.duplication"]\nparams = 3\n')
    with pytest.raises(ValueError, match="params"):
        AnalysisConfig.load(tmp_path, RULE_REGISTRY)


# ---- the init template ----------------------------------------------------------------

def test_the_init_template_loads_as_written(tmp_path: Path):
    from slop import cli
    cli.init(tmp_path)
    assert AnalysisConfig.load(tmp_path, RULE_REGISTRY).rules == \
        AnalysisConfig.defaults(RULE_REGISTRY).rules


def test_the_init_template_loads_with_every_line_uncommented(tmp_path: Path):
    # Uncommenting every generated setting must give exactly the defaults, not an error.
    from slop import cli
    cli.init(tmp_path)
    text = (tmp_path / ".slop.toml").read_text()
    uncommented = "\n".join(
        ln[2:] if ln.startswith("# ") and ("=" in ln or ln.startswith("# [")) and "generated" not in ln
        and "Uncomment" not in ln else ln
        for ln in text.splitlines())
    _write(tmp_path, uncommented)
    loaded = AnalysisConfig.load(tmp_path, RULE_REGISTRY)
    assert loaded.rules == AnalysisConfig.defaults(RULE_REGISTRY).rules
    assert loaded.exclusion.patterns == ("tests/**",)
    assert loaded.languages == frozenset({"python"})
