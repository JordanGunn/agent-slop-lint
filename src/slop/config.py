"""Configuration loading for slop.

Loads config from (in priority order):
1. CLI --config <path> flag
2. .slop.toml in root directory
3. pyproject.toml [tool.slop] section
4. Built-in defaults
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from slop.models import RuleConfig, SlopConfig

# ---------------------------------------------------------------------------
# TOML loading (stdlib on 3.11+, tomli on 3.10)
# ---------------------------------------------------------------------------

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ImportError as e:
        raise ImportError(
            "slop requires 'tomli' on Python < 3.11. Install with: pip install tomli"
        ) from e


# ---------------------------------------------------------------------------
# Built-in defaults
# ---------------------------------------------------------------------------

DEFAULT_RULE_CONFIGS: dict[str, dict[str, Any]] = {
    "complexity": {
        "enabled": True,
        "severity": "error",
        "cyclomatic_threshold": 10,
        "cognitive_threshold": 15,
        "weighted_threshold": 50,
    },
    "hotspots": {
        "enabled": True,
        "severity": "error",
        "since": "14 days ago",
        "min_commits": 2,
        "fail_on_quadrant": ["hotspot"],
    },
    "packages": {
        "enabled": True,
        "severity": "warning",
        "languages": [],
        "max_distance": 0.7,
        "fail_on_zone": ["pain"],
    },
    "deps": {
        "enabled": True,
        "severity": "error",
        "fail_on_cycles": True,
    },
    "orphans": {
        "enabled": False,
        "severity": "warning",
        "min_confidence": "high",
    },
    "class": {
        "enabled": True,
        "severity": "error",
        "coupling_threshold": 8,
        "inheritance_depth_threshold": 4,
        "inheritance_children_threshold": 10,
    },
}


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------


def _read_toml(path: Path) -> dict[str, Any]:
    """Read and parse a TOML file. Returns {} if file doesn't exist."""
    if not path.is_file():
        return {}
    with open(path, "rb") as f:
        return tomllib.load(f)


def _merge_rule_config(
    defaults: dict[str, Any], overrides: dict[str, Any]
) -> RuleConfig:
    """Merge a default rule config dict with user overrides into a RuleConfig."""
    merged = dict(defaults)
    merged.update(overrides)
    enabled = merged.pop("enabled", True)
    severity = merged.pop("severity", "error")
    return RuleConfig(enabled=enabled, severity=severity, params=merged)


def _build_rule_configs(raw_rules: dict[str, Any]) -> dict[str, RuleConfig]:
    """Build RuleConfig dict by merging user config over defaults."""
    result: dict[str, RuleConfig] = {}
    for category, defaults in DEFAULT_RULE_CONFIGS.items():
        user_overrides = raw_rules.get(category, {})
        if not isinstance(user_overrides, dict):
            user_overrides = {}
        result[category] = _merge_rule_config(defaults, user_overrides)
    return result


def load_config(
    *,
    config_path: str | None = None,
    root: str | None = None,
) -> SlopConfig:
    """Load slop configuration from TOML files with fallback to defaults.

    Args:
        config_path: Explicit config file path (highest priority).
        root: Root directory for searching .slop.toml and pyproject.toml.
            If None, uses current directory.

    Returns:
        Merged SlopConfig.
    """
    raw: dict[str, Any] = {}
    search_root = Path(root) if root else Path.cwd()

    # Priority 1: explicit --config path
    if config_path:
        config_file = Path(config_path)
        if not config_file.is_file():
            raise FileNotFoundError(f"Config file not found: {config_file}")
        raw = _read_toml(config_file)
        # If it's a pyproject.toml, extract [tool.slop]
        if config_file.name == "pyproject.toml":
            raw = raw.get("tool", {}).get("slop", {})
    else:
        # Priority 2: .slop.toml in root
        slop_toml = search_root / ".slop.toml"
        if slop_toml.is_file():
            raw = _read_toml(slop_toml)
        else:
            # Priority 3: pyproject.toml [tool.slop]
            pyproject = search_root / "pyproject.toml"
            if pyproject.is_file():
                pyproject_data = _read_toml(pyproject)
                raw = pyproject_data.get("tool", {}).get("slop", {})

    # Extract top-level fields
    config_root = raw.get("root", root or ".")
    languages = raw.get("languages", [])
    exclude = raw.get("exclude", [])

    # Build rule configs
    raw_rules = raw.get("rules", {})
    if not isinstance(raw_rules, dict):
        raw_rules = {}
    rule_configs = _build_rule_configs(raw_rules)

    return SlopConfig(
        root=config_root,
        languages=languages,
        exclude=exclude,
        rules=rule_configs,
    )


PROFILES: dict[str, dict[str, str | int | bool | list[str]]] = {
    "default": {
        "cyclomatic_threshold": 10,
        "cognitive_threshold": 15,
        "weighted_threshold": 50,
        "hotspots_since": "14 days ago",
        "hotspots_min_commits": 2,
        "hotspots_fail_on_quadrant": ["hotspot"],
        "max_distance": 0.7,
        "packages_severity": "warning",
        "orphans_enabled": False,
        "coupling_threshold": 8,
        "inheritance_depth_threshold": 4,
        "inheritance_children_threshold": 10,
    },
    "lax": {
        "cyclomatic_threshold": 20,
        "cognitive_threshold": 25,
        "weighted_threshold": 100,
        "hotspots_since": "90 days ago",
        "hotspots_min_commits": 3,
        "hotspots_fail_on_quadrant": ["hotspot"],
        "max_distance": 0.85,
        "packages_severity": "warning",
        "orphans_enabled": False,
        "coupling_threshold": 15,
        "inheritance_depth_threshold": 6,
        "inheritance_children_threshold": 20,
    },
    "strict": {
        "cyclomatic_threshold": 6,
        "cognitive_threshold": 10,
        "weighted_threshold": 30,
        "hotspots_since": "7 days ago",
        "hotspots_min_commits": 1,
        "hotspots_fail_on_quadrant": ["hotspot", "churning_simple"],
        "max_distance": 0.5,
        "packages_severity": "error",
        "orphans_enabled": True,
        "coupling_threshold": 5,
        "inheritance_depth_threshold": 3,
        "inheritance_children_threshold": 7,
    },
}


def generate_default_config(profile: str = "default") -> str:
    """Generate a .slop.toml config string for the given profile.

    Valid profiles: ``default``, ``lax``, ``strict``.
    """
    if profile not in PROFILES:
        raise ValueError(f"Unknown profile '{profile}'. Valid: {', '.join(sorted(PROFILES))}")
    p = PROFILES[profile]
    quadrant_list = ', '.join(f'"{q}"' for q in p["hotspots_fail_on_quadrant"])
    orphans_enabled = "true" if p["orphans_enabled"] else "false"
    return f'''\
# slop — agentic code quality linter
# https://github.com/JordanGunn/agent-slop-lint
# Profile: {profile}

# Root directory (default: ".")
root = "."

# Languages to analyze (default: auto-detect all supported)
# Supported: python, javascript, typescript, go, rust, java, c_sharp
# languages = ["python", "typescript"]

# Global file exclusions (applied to all rules)
# exclude = ["**/test_*", "**/vendor/**"]

[rules.complexity]
enabled = true
cyclomatic_threshold = {p["cyclomatic_threshold"]}       # fail if any function CCX exceeds this
cognitive_threshold = {p["cognitive_threshold"]}        # fail if any function CogC exceeds this
weighted_threshold = {p["weighted_threshold"]}         # fail if any class WMC exceeds this
severity = "error"

[rules.hotspots]
enabled = true
since = "{p["hotspots_since"]}"
min_commits = {p["hotspots_min_commits"]}
fail_on_quadrant = [{quadrant_list}]
severity = "error"

[rules.packages]
enabled = true
# languages = ["python"]        # robert metrics only support go and python
max_distance = {p["max_distance"]}
fail_on_zone = ["pain"]
severity = "{p["packages_severity"]}"

[rules.deps]
enabled = true
fail_on_cycles = true
severity = "error"

[rules.orphans]
enabled = {orphans_enabled}
min_confidence = "high"
severity = "warning"

[rules.class]
enabled = true
coupling_threshold = {p["coupling_threshold"]}
inheritance_depth_threshold = {p["inheritance_depth_threshold"]}
inheritance_children_threshold = {p["inheritance_children_threshold"]}
severity = "error"
'''
