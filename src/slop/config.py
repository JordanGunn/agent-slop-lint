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
        "since": "90 days ago",
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


def generate_default_config() -> str:
    """Generate a default .slop.toml config string."""
    return '''\
# slop — agentic code quality linter
# https://github.com/JordanGunn/slop

# Root directory (default: ".")
root = "."

# Languages to analyze (default: auto-detect all supported)
# Supported: python, javascript, typescript, go, rust, java
# languages = ["python", "typescript"]

# Global file exclusions (applied to all rules)
# exclude = ["**/test_*", "**/vendor/**"]

[rules.complexity]
enabled = true
cyclomatic_threshold = 10       # fail if any function CCX exceeds this
cognitive_threshold = 15        # fail if any function CogC exceeds this
weighted_threshold = 50         # fail if any class WMC exceeds this
severity = "error"

[rules.hotspots]
enabled = true
since = "90 days ago"           # git log window (agentic-era default: 90d)
min_commits = 2
fail_on_quadrant = ["hotspot"]
severity = "error"

[rules.packages]
enabled = true
# languages = ["python"]        # robert metrics only support go and python
max_distance = 0.7              # fail if D\\' exceeds this
fail_on_zone = ["pain"]
severity = "warning"

[rules.deps]
enabled = true
fail_on_cycles = true
severity = "error"

[rules.orphans]
enabled = false                 # off by default — advisory, needs human review
min_confidence = "high"
severity = "warning"

[rules.class]
enabled = true
coupling_threshold = 8          # CBO: max other classes this class depends on
inheritance_depth_threshold = 4 # DIT: max inheritance tree depth
inheritance_children_threshold = 10  # NOC: max direct subclasses
severity = "error"
'''
