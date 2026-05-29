"""Tests for slop config loading.

Under the scope-as-first-class design, rule names are bare (no scope
prefix) and per-scope thresholds live in a nested ``thresholds`` dict.
Loader.py merges nested ``thresholds`` so a user override of one scope
keeps other scope defaults intact.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from slop.cli.templates import generate_default_config
from slop.config import Config
from slop.config.loader import DEFAULT_RULE_CONFIGS, load_config

# ---------------------------------------------------------------------------
# 1. Default config
# ---------------------------------------------------------------------------


def test_load_defaults_when_no_config_files(tmp_path: Path):
    config = load_config(root=str(tmp_path))
    assert isinstance(config, Config)
    assert config.root == str(tmp_path)
    assert config.languages == []
    assert config.exclude == []


def test_default_complexity_function_thresholds(tmp_path: Path):
    config = load_config(root=str(tmp_path))
    cyc = config.rule_config("complexity.cyclomatic")
    cog = config.rule_config("complexity.cognitive")
    comb = config.rule_config("complexity.combinatorial")
    assert cyc.enabled and cyc.severity == "error"
    assert cyc.params["thresholds"]["function"] == 10
    assert cog.params["thresholds"]["function"] == 15
    assert comb.params["thresholds"]["function"] == 400


def test_default_complexity_class_thresholds(tmp_path: Path):
    config = load_config(root=str(tmp_path))
    assert config.rule_config("complexity.cyclomatic").params["thresholds"]["class"] == 40
    # cognitive / combinatorial class-scope: slop calibration defaults.
    assert config.rule_config("complexity.cognitive").params["thresholds"]["class"] == 60
    assert config.rule_config("complexity.combinatorial").params["thresholds"]["class"] == 1600


def test_default_density_function_scope_only(tmp_path: Path):
    config = load_config(root=str(tmp_path))
    rc = config.rule_config("complexity.density")
    assert rc.params["thresholds"] == {"function": 30}


def test_default_hotspots_since_14_days(tmp_path: Path):
    config = load_config(root=str(tmp_path))
    rc = config.rule_config("hotspots")
    assert rc.enabled is True
    assert rc.params["since"] == "14 days ago"
    assert rc.params["min_commits"] == 2
    assert rc.params["fail_on_quadrant"] == ["hotspot"]


def test_default_orphans_disabled(tmp_path: Path):
    config = load_config(root=str(tmp_path))
    rc = config.rule_config("orphans")
    assert rc.enabled is False
    assert rc.severity == "warning"


def test_default_rigidity_threshold(tmp_path: Path):
    config = load_config(root=str(tmp_path))
    rc = config.rule_config("rigidity")
    assert rc.severity == "warning"
    assert rc.params["thresholds"]["package"] == 0.7


def test_default_uselessness_threshold(tmp_path: Path):
    config = load_config(root=str(tmp_path))
    rc = config.rule_config("uselessness")
    assert rc.severity == "warning"
    assert rc.params["thresholds"]["package"] == 0.7


def test_default_deps_fail_on_cycles(tmp_path: Path):
    config = load_config(root=str(tmp_path))
    rc = config.rule_config("deps")
    assert rc.params["fail_on_cycles"] is True


def test_default_ck_class_thresholds(tmp_path: Path):
    config = load_config(root=str(tmp_path))
    assert config.rule_config("coupling").params["thresholds"]["class"] == 8
    assert config.rule_config("inheritance.depth").params["thresholds"]["class"] == 4
    assert config.rule_config("inheritance.children").params["thresholds"]["class"] == 10


def test_default_all_categories_present(tmp_path: Path):
    config = load_config(root=str(tmp_path))
    for category in DEFAULT_RULE_CONFIGS:
        assert category in config.rules, f"Missing default rule: {category}"


# ---------------------------------------------------------------------------
# 2. .slop.toml loading
# ---------------------------------------------------------------------------


def test_load_from_slop_toml(tmp_path: Path):
    (tmp_path / ".slop.toml").write_text(
        """\
root = "src"
languages = ["python"]
exclude = ["**/vendor/**"]

[rules.complexity.cyclomatic]
thresholds = { function = 20 }
"""
    )
    config = load_config(root=str(tmp_path))
    assert Path(config.root) == (tmp_path / "src").resolve()
    assert config.config_path == (tmp_path / ".slop.toml").resolve()
    assert config.languages == ["python"]
    assert config.exclude == ["**/vendor/**"]
    cyc = config.rule_config("complexity.cyclomatic")
    # User override applied to function scope.
    assert cyc.params["thresholds"]["function"] == 20
    # Class scope default preserved by the deep-merge.
    assert cyc.params["thresholds"]["class"] == 40
    # Sibling cognitive rule untouched.
    cog = config.rule_config("complexity.cognitive")
    assert cog.params["thresholds"]["function"] == 15


def test_threshold_override_deep_merges(tmp_path: Path):
    """User overrides one scope; the other scope keeps its default."""
    (tmp_path / ".slop.toml").write_text(
        """\
[rules.complexity.cyclomatic]
thresholds = { class = 999 }
"""
    )
    config = load_config(root=str(tmp_path))
    rc = config.rule_config("complexity.cyclomatic")
    # Class override applied; function default preserved.
    assert rc.params["thresholds"]["class"] == 999
    assert rc.params["thresholds"]["function"] == 10


def test_loads_top_level_waivers(tmp_path: Path):
    (tmp_path / ".slop.toml").write_text(
        """\
[[waivers]]
id = "parser-npath"
path = "src/parser/**"
rule = "complexity.combinatorial"
allow_up_to = 1200
reason = "Parser branch shape mirrors grammar alternatives."
expires = "2099-01-01"
"""
    )
    config = load_config(root=str(tmp_path))
    assert len(config.waivers) == 1
    waiver = config.waivers[0]
    assert waiver.id == "parser-npath"
    assert waiver.path == "src/parser/**"
    assert waiver.rule == "complexity.combinatorial"
    assert waiver.allow_up_to == 1200
    assert waiver.reason.startswith("Parser branch")
    assert waiver.expires == "2099-01-01"


def test_waiver_requires_reason(tmp_path: Path):
    (tmp_path / ".slop.toml").write_text(
        """\
[[waivers]]
id = "missing-reason"
path = "src/parser/**"
rule = "complexity.combinatorial"
"""
    )
    with pytest.raises(ValueError, match="reason"):
        load_config(root=str(tmp_path))


def test_waiver_rejects_duplicate_ids(tmp_path: Path):
    (tmp_path / ".slop.toml").write_text(
        """\
[[waivers]]
id = "same"
path = "a.py"
rule = "complexity.combinatorial"
reason = "one"

[[waivers]]
id = "same"
path = "b.py"
rule = "complexity.combinatorial"
reason = "two"
"""
    )
    with pytest.raises(ValueError, match="duplicate waiver id"):
        load_config(root=str(tmp_path))


def test_slop_toml_overrides_pyproject(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text('[tool.slop]\nroot = "from_pyproject"\n')
    (tmp_path / ".slop.toml").write_text('root = "from_slop_toml"\n')
    config = load_config(root=str(tmp_path))
    assert Path(config.root) == (tmp_path / "from_slop_toml").resolve()


# ---------------------------------------------------------------------------
# 3. pyproject.toml loading
# ---------------------------------------------------------------------------


def test_load_from_pyproject_tool_slop(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text(
        """\
[tool.slop]
root = "lib"

[tool.slop.rules.complexity.cyclomatic]
thresholds = { function = 5 }
severity = "warning"
"""
    )
    config = load_config(root=str(tmp_path))
    assert Path(config.root) == (tmp_path / "lib").resolve()
    assert config.config_path == (tmp_path / "pyproject.toml").resolve()
    rc = config.rule_config("complexity.cyclomatic")
    assert rc.params["thresholds"]["function"] == 5
    assert rc.severity == "warning"


def test_pyproject_without_tool_slop_section_gives_defaults(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "something-else"\n')
    config = load_config(root=str(tmp_path))
    rc = config.rule_config("complexity.cyclomatic")
    assert rc.params["thresholds"]["function"] == 10


# ---------------------------------------------------------------------------
# 4. Explicit --config path
# ---------------------------------------------------------------------------


def test_explicit_config_path(tmp_path: Path):
    custom = tmp_path / "custom.toml"
    custom.write_text(
        '[rules.deps]\nfail_on_cycles = false\nroot = "custom_root"\n'
    )
    config = load_config(config_path=str(custom))
    rc = config.rule_config("deps")
    assert rc.params["fail_on_cycles"] is False


def test_explicit_config_path_not_found_raises(tmp_path: Path):
    with pytest.raises(FileNotFoundError, match="Config file not found"):
        load_config(config_path=str(tmp_path / "nonexistent.toml"))


def test_explicit_pyproject_extracts_tool_slop(tmp_path: Path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[tool.slop]\nroot = "from_explicit_pyproject"\n')
    config = load_config(config_path=str(pyproject))
    assert Path(config.root) == (tmp_path / "from_explicit_pyproject").resolve()


# ---------------------------------------------------------------------------
# 5. Rule config merging
# ---------------------------------------------------------------------------


def test_disable_rule_via_config(tmp_path: Path):
    (tmp_path / ".slop.toml").write_text(
        "[rules.hotspots]\nenabled = false\n"
    )
    config = load_config(root=str(tmp_path))
    rc = config.rule_config("hotspots")
    assert rc.enabled is False
    assert rc.params["since"] == "14 days ago"


def test_unknown_category_returns_default_rule_config(tmp_path: Path):
    config = load_config(root=str(tmp_path))
    rc = config.rule_config("nonexistent")
    assert rc.enabled is True
    assert rc.severity == "error"
    assert rc.params == {}


# ---------------------------------------------------------------------------
# 6. Upward config discovery
# ---------------------------------------------------------------------------


def test_upward_walk_finds_parent_slop_toml(tmp_path: Path):
    (tmp_path / ".slop.toml").write_text(
        'root = "src"\n[rules.complexity.cyclomatic]\nthresholds = { function = 7 }\n'
    )
    deep = tmp_path / "a" / "b" / "c"
    deep.mkdir(parents=True)
    config = load_config(root=str(deep))
    assert config.config_path == (tmp_path / ".slop.toml").resolve()
    assert Path(config.root) == (tmp_path / "src").resolve()
    assert config.rule_config("complexity.cyclomatic").params["thresholds"]["function"] == 7


def test_upward_walk_finds_parent_pyproject(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text('[tool.slop]\nroot = "lib"\n')
    deep = tmp_path / "inner"
    deep.mkdir()
    config = load_config(root=str(deep))
    assert config.config_path == (tmp_path / "pyproject.toml").resolve()
    assert Path(config.root) == (tmp_path / "lib").resolve()


def test_pyproject_without_tool_slop_does_not_halt_walk(tmp_path: Path):
    outer = tmp_path
    outer_slop = outer / ".slop.toml"
    outer_slop.write_text(
        '[rules.complexity.cyclomatic]\nthresholds = { function = 99 }\n'
    )
    inner = tmp_path / "sub"
    inner.mkdir()
    (inner / "pyproject.toml").write_text('[project]\nname = "x"\n')
    config = load_config(root=str(inner))
    assert config.config_path == outer_slop.resolve()
    assert config.rule_config("complexity.cyclomatic").params["thresholds"]["function"] == 99


def test_absolute_root_in_config_stays_absolute(tmp_path: Path):
    target = tmp_path / "explicit_abs"
    target.mkdir()
    (tmp_path / ".slop.toml").write_text(f'root = "{target}"\n')
    config = load_config(root=str(tmp_path))
    assert config.root == str(target)


def test_no_config_found_populates_config_path_none(tmp_path: Path):
    config = load_config(root=str(tmp_path))
    assert config.config_path is None


# ---------------------------------------------------------------------------
# 7. Config generation
# ---------------------------------------------------------------------------


def test_generate_default_config_is_valid_toml(tmp_path: Path):
    content = generate_default_config()
    assert isinstance(content, str)
    # Complexity family (bare names)
    assert "[rules.complexity.cyclomatic]" in content
    assert "[rules.complexity.cognitive]" in content
    assert "[rules.complexity.combinatorial]" in content
    assert "[rules.complexity.volume]" in content
    assert "[rules.complexity.density]" in content
    # Standalone scope-determined rules
    assert "[rules.coupling]" in content
    assert "[rules.inheritance.depth]" in content
    assert "[rules.god_module]" in content
    assert "[rules.escape_hatches]" in content
    assert "[rules.sentinels]" in content
    assert "[rules.rigidity]" in content
    assert "[rules.uselessness]" in content
    # Cross-cutting (no scope)
    assert "[rules.hotspots]" in content
    assert "[rules.deps]" in content
    assert "[rules.orphans]" in content
    # Round-trip: the generated template loads back to the defaults.
    config_file = tmp_path / ".slop.toml"
    config_file.write_text(content)
    config = load_config(root=str(tmp_path))
    assert config.rule_config("complexity.cyclomatic").params["thresholds"]["function"] == 10


def test_generated_template_covers_every_registered_rule():
    """`slop init` must emit a loader-visible table for EVERY rule.

    Guards two regressions at once: rules silently omitted from the
    template (slackers/confusion/runts were), and a table form the loader
    can't resolve (the scope-first `[rules.function.complexity.*]` drift,
    which mapped to no canonical key and fell back to defaults).
    """
    import tomllib

    from slop.config.loader import _flatten_canonical_tables
    from slop.linter import RULE_REGISTRY

    raw = tomllib.loads(generate_default_config("default"))["rules"]
    canonical = {rd.name for rd in RULE_REGISTRY}
    recovered = set(_flatten_canonical_tables(raw, canonical))
    assert canonical - recovered == set(), (
        f"template omits or mis-keys: {sorted(canonical - recovered)}"
    )


def test_generated_template_round_trips_to_default_thresholds(tmp_path: Path):
    """Every rule's per-scope thresholds must survive template -> loader.

    A scope-prefixed table (`[rules.function.complexity.cyclomatic]`)
    parses fine but resolves to no canonical key, so the rule silently
    runs on built-in defaults. This asserts the emitted thresholds are
    actually consumed, not coincidentally equal to defaults.
    """
    (tmp_path / ".slop.toml").write_text(generate_default_config("default"))
    config = load_config(root=str(tmp_path))
    for name, default in DEFAULT_RULE_CONFIGS.items():
        want = default.get("thresholds")
        got = config.rule_config(name).params.get("thresholds")
        assert want == got, f"{name}: template thresholds {got} != default {want}"
