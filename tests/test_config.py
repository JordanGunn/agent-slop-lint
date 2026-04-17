"""Tests for slop config loading."""

from __future__ import annotations

from pathlib import Path

import pytest

from slop.config import (
    DEFAULT_RULE_CONFIGS,
    generate_default_config,
    load_config,
)
from slop.models import SlopConfig

# ---------------------------------------------------------------------------
# 1. Default config
# ---------------------------------------------------------------------------


def test_load_defaults_when_no_config_files(tmp_path: Path):
    config = load_config(root=str(tmp_path))
    assert isinstance(config, SlopConfig)
    assert config.root == str(tmp_path)
    assert config.languages == []
    assert config.exclude == []


def test_default_complexity_enabled_with_standard_thresholds(tmp_path: Path):
    config = load_config(root=str(tmp_path))
    rc = config.rule_config("complexity")
    assert rc.enabled is True
    assert rc.severity == "error"
    assert rc.params["cyclomatic_threshold"] == 10
    assert rc.params["cognitive_threshold"] == 15
    assert rc.params["weighted_threshold"] == 50


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


def test_default_packages_severity_warning(tmp_path: Path):
    config = load_config(root=str(tmp_path))
    rc = config.rule_config("packages")
    assert rc.severity == "warning"
    assert rc.params["max_distance"] == 0.7
    assert rc.params["fail_on_zone"] == ["pain"]


def test_default_deps_fail_on_cycles(tmp_path: Path):
    config = load_config(root=str(tmp_path))
    rc = config.rule_config("deps")
    assert rc.params["fail_on_cycles"] is True


def test_default_class_thresholds(tmp_path: Path):
    config = load_config(root=str(tmp_path))
    rc = config.rule_config("class")
    assert rc.enabled is True
    assert rc.params["coupling_threshold"] == 8
    assert rc.params["inheritance_depth_threshold"] == 4
    assert rc.params["inheritance_children_threshold"] == 10


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

[rules.complexity]
cyclomatic_threshold = 20
"""
    )
    config = load_config(root=str(tmp_path))
    # Relative config roots are now resolved against the config file's
    # directory (ruff/mypy convention).
    assert Path(config.root) == (tmp_path / "src").resolve()
    assert config.config_path == (tmp_path / ".slop.toml").resolve()
    assert config.languages == ["python"]
    assert config.exclude == ["**/vendor/**"]
    rc = config.rule_config("complexity")
    assert rc.params["cyclomatic_threshold"] == 20
    assert rc.params["cognitive_threshold"] == 15


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

[tool.slop.rules.complexity]
cyclomatic_threshold = 5
severity = "warning"
"""
    )
    config = load_config(root=str(tmp_path))
    assert Path(config.root) == (tmp_path / "lib").resolve()
    assert config.config_path == (tmp_path / "pyproject.toml").resolve()
    rc = config.rule_config("complexity")
    assert rc.params["cyclomatic_threshold"] == 5
    assert rc.severity == "warning"


def test_pyproject_without_tool_slop_section_gives_defaults(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "something-else"\n')
    config = load_config(root=str(tmp_path))
    rc = config.rule_config("complexity")
    assert rc.params["cyclomatic_threshold"] == 10


# ---------------------------------------------------------------------------
# 4. Explicit --config path
# ---------------------------------------------------------------------------


def test_explicit_config_path(tmp_path: Path):
    custom = tmp_path / "custom.toml"
    custom.write_text('[rules.deps]\nfail_on_cycles = false\nroot = "custom_root"\n')
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
    (tmp_path / ".slop.toml").write_text("[rules.hotspots]\nenabled = false\n")
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
    """Running from a deep subdirectory still finds .slop.toml at the root."""
    (tmp_path / ".slop.toml").write_text('root = "src"\n[rules.complexity]\ncyclomatic_threshold = 7\n')
    deep = tmp_path / "a" / "b" / "c"
    deep.mkdir(parents=True)
    config = load_config(root=str(deep))
    # Config discovered at tmp_path; its "src" resolves relative to tmp_path.
    assert config.config_path == (tmp_path / ".slop.toml").resolve()
    assert Path(config.root) == (tmp_path / "src").resolve()
    assert config.rule_config("complexity").params["cyclomatic_threshold"] == 7


def test_upward_walk_finds_parent_pyproject(tmp_path: Path):
    """pyproject.toml with [tool.slop] in a parent directory is honored."""
    (tmp_path / "pyproject.toml").write_text('[tool.slop]\nroot = "lib"\n')
    deep = tmp_path / "inner"
    deep.mkdir()
    config = load_config(root=str(deep))
    assert config.config_path == (tmp_path / "pyproject.toml").resolve()
    assert Path(config.root) == (tmp_path / "lib").resolve()


def test_pyproject_without_tool_slop_stops_upward_walk(tmp_path: Path):
    """A pyproject.toml with no [tool.slop] section still halts the walk."""
    # Outer: a .slop.toml that would otherwise be discovered.
    outer = tmp_path
    outer_slop = outer / ".slop.toml"
    outer_slop.write_text('[rules.complexity]\ncyclomatic_threshold = 99\n')
    # Inner: a pyproject.toml without [tool.slop], acts as project boundary.
    inner = tmp_path / "sub"
    inner.mkdir()
    (inner / "pyproject.toml").write_text('[project]\nname = "x"\n')
    config = load_config(root=str(inner))
    # Walk stopped at inner/pyproject.toml (no [tool.slop]) — falls back to
    # defaults, NOT outer's .slop.toml.
    assert config.config_path == (inner / "pyproject.toml").resolve()
    assert config.rule_config("complexity").params["cyclomatic_threshold"] == 10


def test_absolute_root_in_config_stays_absolute(tmp_path: Path):
    """An absolute `root` in config is used verbatim, not re-resolved."""
    target = tmp_path / "explicit_abs"
    target.mkdir()
    (tmp_path / ".slop.toml").write_text(f'root = "{target}"\n')
    config = load_config(root=str(tmp_path))
    assert config.root == str(target)


def test_no_config_found_populates_config_path_none(tmp_path: Path):
    """Falling back to defaults leaves config_path unset."""
    config = load_config(root=str(tmp_path))
    assert config.config_path is None


# ---------------------------------------------------------------------------
# 7. Config generation
# ---------------------------------------------------------------------------


def test_generate_default_config_is_valid_toml(tmp_path: Path):
    content = generate_default_config()
    assert isinstance(content, str)
    assert "[rules.complexity]" in content
    assert "[rules.hotspots]" in content
    assert "[rules.orphans]" in content
    assert "[rules.packages]" in content
    assert "[rules.deps]" in content
    assert "[rules.class]" in content
    config_file = tmp_path / ".slop.toml"
    config_file.write_text(content)
    config = load_config(root=str(tmp_path))
    assert config.rule_config("complexity").params["cyclomatic_threshold"] == 10
