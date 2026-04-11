"""Tests for slop config loading."""

from __future__ import annotations

from pathlib import Path

import pytest

from slop.config import (
    DEFAULT_RULE_CONFIGS,
    generate_default_config,
    load_config,
)
from slop.models import RuleConfig, SlopConfig


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


def test_default_hotspots_since_90_days(tmp_path: Path):
    config = load_config(root=str(tmp_path))
    rc = config.rule_config("hotspots")
    assert rc.enabled is True
    assert rc.params["since"] == "90 days ago"
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
    assert config.root == "src"
    assert config.languages == ["python"]
    assert config.exclude == ["**/vendor/**"]
    rc = config.rule_config("complexity")
    assert rc.params["cyclomatic_threshold"] == 20
    assert rc.params["cognitive_threshold"] == 15


def test_slop_toml_overrides_pyproject(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text('[tool.slop]\nroot = "from_pyproject"\n')
    (tmp_path / ".slop.toml").write_text('root = "from_slop_toml"\n')
    config = load_config(root=str(tmp_path))
    assert config.root == "from_slop_toml"


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
    assert config.root == "lib"
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
    assert config.root == "from_explicit_pyproject"


# ---------------------------------------------------------------------------
# 5. Rule config merging
# ---------------------------------------------------------------------------


def test_disable_rule_via_config(tmp_path: Path):
    (tmp_path / ".slop.toml").write_text("[rules.hotspots]\nenabled = false\n")
    config = load_config(root=str(tmp_path))
    rc = config.rule_config("hotspots")
    assert rc.enabled is False
    assert rc.params["since"] == "90 days ago"


def test_unknown_category_returns_default_rule_config(tmp_path: Path):
    config = load_config(root=str(tmp_path))
    rc = config.rule_config("nonexistent")
    assert rc.enabled is True
    assert rc.severity == "error"
    assert rc.params == {}


# ---------------------------------------------------------------------------
# 6. Config generation
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
