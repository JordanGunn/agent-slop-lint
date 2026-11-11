"""Config: `exclude` and `[rules.<name>]` tables, and what is rejected."""
from __future__ import annotations

from pathlib import Path

import pytest

from slop import cli
from slop.config import AnalysisConfig
from slop.rules import RULE_REGISTRY
from slop.scope import scan_corpus


def _write(root: Path, text: str) -> None:
    (root / ".slop.toml").write_text(text)


def _load(root: Path) -> AnalysisConfig:
    return AnalysisConfig.load(root, RULE_REGISTRY)


def test_defaults_cover_every_rule_and_every_rule_is_on():
    config = AnalysisConfig.defaults(RULE_REGISTRY)
    assert set(config.rules) == {r.name for r in RULE_REGISTRY}
    assert all(rc.enabled for rc in config.rules.values())


def test_no_config_file_means_defaults(tmp_path: Path):
    assert _load(tmp_path) == AnalysisConfig.defaults(RULE_REGISTRY)


def test_a_limit_override_applies_to_that_rule_only(tmp_path: Path):
    _write(tmp_path, "[rules.cyclomatic-complexity]\nlimit = 3\n")
    config = _load(tmp_path)
    assert config.for_rule("cyclomatic-complexity").option("limit") == 3
    assert config.for_rule("cognitive-complexity").option("limit") == 15


def test_a_rule_can_be_disabled_and_a_default_off_rule_enabled(tmp_path: Path):
    _write(tmp_path, "[rules.god-module]\nenabled = false\n[rules.class-cohesion]\nenabled = true\n")
    config = _load(tmp_path)
    assert config.for_rule("god-module").enabled is False
    assert config.for_rule("class-cohesion").enabled is True
    assert config.for_rule("class-cohesion").option("limit") == 1      # option default kept


def test_a_whole_number_is_accepted_for_a_fractional_limit(tmp_path: Path):
    _write(tmp_path, "[rules.rigid-package]\nlimit = 1\n")
    assert _load(tmp_path).for_rule("rigid-package").option("limit") == 1


@pytest.mark.parametrize("text, message", [
    ("[rules.no-such-rule]\nenabled = true\n", "unknown rule"),
    ('[rules."complexity.cyclomatic"]\nlimit = 3\n', "unknown rule"),            # the old dotted name
    ("[rules.cyclomatic-complexity]\nthreshold = 3\n", "unknown option"),
    ("[rules.cyclomatic-complexity]\nseverity = 'error'\n", "unknown option"),
    ("[rules.cyclomatic-complexity]\nlimit = 'ten'\n", "must be of type"),
    ("[rules.cyclomatic-complexity]\nlimit = true\n", "must be of type"),         # a bool is not a number
    ("[rules.cyclomatic-complexity]\nenabled = 1\n", "'enabled' must be"),
    ("[rules.cyclomatic-complexity]\nlimit = 2.5\n", "must be of type"),            # a count is whole
    ("[rules.duplicate-code]\nmin_leaf_nodes = 2.5\n", "must be of type"),
    ("rules.cyclomatic-complexity = 3\n", "expected a table"),
    ("[rules.import-cycle]\nlimit = 1\n", "unknown option"),                       # declares no options
])
def test_a_config_that_could_silently_do_nothing_is_an_error(tmp_path: Path, text: str, message: str):
    _write(tmp_path, text)
    with pytest.raises(ValueError, match=message):
        _load(tmp_path)


@pytest.mark.parametrize("key", ["languages", "ignore", "severity", "thresholds", "root"])
def test_only_exclude_and_rules_are_top_level_keys(tmp_path: Path, key: str):
    _write(tmp_path, f"{key} = []\n")
    with pytest.raises(ValueError, match="unknown key"):
        _load(tmp_path)


def test_exclude_globs_are_relative_to_the_config_directory(tmp_path: Path):
    _write(tmp_path, 'exclude = ["tests/**", "gen_*.py"]\n')
    config = _load(tmp_path)
    assert config.excludes(tmp_path / "tests" / "unit" / "test_a.py")     # `*` crosses `/`
    assert config.excludes(tmp_path / "gen_a.py")
    assert not config.excludes(tmp_path / "src" / "tests_helper.py")
    assert not config.excludes(tmp_path.parent / "tests" / "x.py")        # outside the config dir


def test_exclude_must_be_a_list_of_strings(tmp_path: Path):
    _write(tmp_path, 'exclude = "tests/**"\n')
    with pytest.raises(ValueError, match="exclude"):
        _load(tmp_path)


def test_excluded_files_are_not_carved(tmp_path: Path):
    (tmp_path / "keep.py").write_text("def f():\n    return 1\n")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_x.py").write_text("def g():\n    return 1\n")
    _write(tmp_path, 'exclude = ["tests/**"]\n')
    corpus = scan_corpus(tmp_path, _load(tmp_path))
    assert {c.qualname for c in corpus._iter_callables()} == {"keep.f"}


def test_config_is_found_in_pyproject_and_a_slop_toml_wins(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text("[tool.slop.rules.god-module]\nlimit = 7\n")
    assert _load(tmp_path).for_rule("god-module").option("limit") == 7
    _write(tmp_path, "[rules.god-module]\nlimit = 9\n")
    assert _load(tmp_path).for_rule("god-module").option("limit") == 9


def test_a_pyproject_without_a_slop_table_does_not_hide_a_config_above_it(tmp_path: Path):
    _write(tmp_path, "[rules.god-module]\nlimit = 9\n")
    sub = tmp_path / "pkg"
    sub.mkdir()
    (sub / "pyproject.toml").write_text("[project]\nname = 'x'\n")
    assert _load(sub).for_rule("god-module").option("limit") == 9


def test_the_init_template_loads_as_written_and_changes_nothing(tmp_path: Path):
    cli.config.init(tmp_path)
    template = (tmp_path / ".slop.toml").read_text()
    # Uncomment every generated setting: the result must be the defaults, not an error.
    uncommented = "\n".join(
        line[2:] if line.startswith("# ") and ("=" in line or line.startswith("# [")) else line
        for line in template.splitlines())
    (tmp_path / ".slop.toml").write_text(uncommented)
    loaded = _load(tmp_path)
    assert loaded.rules == AnalysisConfig.defaults(RULE_REGISTRY).rules
    assert loaded.exclude == ("tests/**",)
