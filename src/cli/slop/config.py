"""Configuration loading for slop.

Loads config from (in priority order):
1. CLI --config <path> flag
2. .slop.toml in root directory
3. pyproject.toml [tool.slop] section
4. Built-in defaults
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
from typing import Any

from slop.models import RuleConfig, SlopConfig, WaiverConfig

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
        "weighted_threshold": 40,
    },
    "halstead": {
        "enabled": True,
        "severity": "error",
        "volume_threshold": 1500,
        "difficulty_threshold": 30,
    },
    "npath": {
        "enabled": True,
        "severity": "error",
        "npath_threshold": 400,
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


def _build_waivers(raw_waivers: Any) -> list[WaiverConfig]:
    """Build and validate top-level waiver configuration."""
    if raw_waivers is None:
        return []
    if not isinstance(raw_waivers, list):
        raise ValueError("waivers must be an array of tables")

    waivers: list[WaiverConfig] = []
    seen_ids: set[str] = set()
    for i, raw in enumerate(raw_waivers, start=1):
        waiver = _build_waiver(raw, i, seen_ids)
        waivers.append(waiver)
    return waivers


def _build_waiver(raw: Any, index: int, seen_ids: set[str]) -> WaiverConfig:
    """Build one waiver from a TOML table."""
    if not isinstance(raw, dict):
        raise ValueError(f"waiver #{index} must be a table")

    waiver_id = _required_string(raw, "id", f"waiver #{index}")
    if waiver_id in seen_ids:
        raise ValueError(f"duplicate waiver id: {waiver_id}")
    seen_ids.add(waiver_id)

    return WaiverConfig(
        id=waiver_id,
        path=_required_string(raw, "path", f"waiver {waiver_id}"),
        rule=_required_string(raw, "rule", f"waiver {waiver_id}"),
        reason=_required_string(raw, "reason", f"waiver {waiver_id}"),
        allow_up_to=_optional_number(raw, "allow_up_to", f"waiver {waiver_id}"),
        expires=_optional_iso_date(raw, "expires", f"waiver {waiver_id}"),
    )


def _required_string(raw: dict[str, Any], key: str, label: str) -> str:
    """Read a required non-empty string field."""
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must define a non-empty {key}")
    return value


def _optional_number(raw: dict[str, Any], key: str, label: str) -> float | int | None:
    """Read an optional non-bool numeric field."""
    value = raw.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{label} {key} must be numeric")
    return value


def _optional_iso_date(raw: dict[str, Any], key: str, label: str) -> str | None:
    """Read an optional ISO date string."""
    value = raw.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{label} {key} must be an ISO date string")
    try:
        date.fromisoformat(value)
    except ValueError as e:
        raise ValueError(f"{label} {key} must be an ISO date string") from e
    return value


def _discover_config(search_root: Path) -> tuple[Path | None, dict[str, Any]]:
    """Walk upward from search_root looking for a slop config file.

    At each directory: ``.slop.toml`` wins outright. A ``pyproject.toml``
    counts only if it has a ``[tool.slop]`` table; one without is not a
    slop config and the walk continues upward. This lets sub-project
    pyproject files (e.g. src/pyproject.toml in a nested layout) coexist
    with a repo-root ``.slop.toml``.

    Returns the discovered config file path (or None) and the parsed dict.
    """
    current = search_root.resolve()
    while True:
        slop_toml = current / ".slop.toml"
        if slop_toml.is_file():
            return slop_toml, _read_toml(slop_toml)
        pyproject = current / "pyproject.toml"
        if pyproject.is_file():
            data = _read_toml(pyproject)
            slop_table = data.get("tool", {}).get("slop", {})
            if slop_table:
                return pyproject, slop_table
        if current.parent == current:
            return None, {}
        current = current.parent


def load_config(
    *,
    config_path: str | None = None,
    root: str | None = None,
) -> SlopConfig:
    """Load slop configuration from TOML files with fallback to defaults.

    Discovery walks upward from ``root`` (or CWD) looking for ``.slop.toml``
    or ``pyproject.toml`` with a ``[tool.slop]`` table — matching the
    convention used by ruff, mypy, etc. Relative ``root`` paths in a
    discovered config are resolved relative to the config file's directory;
    explicit ``--config`` paths are resolved relative to CWD.

    Args:
        config_path: Explicit config file path (highest priority, no walk).
        root: Starting directory for the upward walk. If None, uses CWD.

    Returns:
        Merged SlopConfig with ``config_path`` populated when a config was
        discovered (or None when falling back to defaults).
    """
    raw: dict[str, Any] = {}
    search_root = Path(root) if root else Path.cwd()
    discovered_config: Path | None = None

    # Priority 1: explicit --config path (no upward walk)
    if config_path:
        config_file = Path(config_path)
        if not config_file.is_file():
            raise FileNotFoundError(f"Config file not found: {config_file}")
        raw = _read_toml(config_file)
        if config_file.name == "pyproject.toml":
            raw = raw.get("tool", {}).get("slop", {})
        discovered_config = config_file.resolve()
    else:
        # Priority 2/3: walk upward looking for .slop.toml or pyproject.toml
        discovered_config, raw = _discover_config(search_root)

    # Extract top-level fields
    raw_root = raw.get("root")
    languages = raw.get("languages", [])
    exclude = raw.get("exclude", [])
    waivers = _build_waivers(raw.get("waivers"))

    # Resolve root. Precedence:
    #   - config's `root` (resolved relative to the config file's directory
    #     when the config was discovered) wins when present.
    #   - the caller-supplied ``root`` is used as a fallback.
    #   - final fallback is ".".
    # CLI ``--root`` overrides are applied by the caller after load_config
    # returns (see slop.cli._load_and_run); this function treats its ``root``
    # parameter only as a search-start hint and default.
    if raw_root is not None:
        raw_root_path = Path(raw_root)
        if raw_root_path.is_absolute() or discovered_config is None:
            config_root = str(raw_root_path)
        else:
            config_root = str((discovered_config.parent / raw_root_path).resolve())
    elif root is not None:
        config_root = root
    else:
        config_root = "."

    # Build rule configs
    raw_rules = raw.get("rules", {})
    if not isinstance(raw_rules, dict):
        raw_rules = {}
    rule_configs = _build_rule_configs(raw_rules)

    return SlopConfig(
        root=config_root,
        languages=languages,
        exclude=exclude,
        waivers=waivers,
        rules=rule_configs,
        config_path=discovered_config,
    )


PROFILES: dict[str, dict[str, str | int | bool | list[str]]] = {
    "default": {
        "cyclomatic_threshold": 10,
        "cognitive_threshold": 15,
        "weighted_threshold": 40,
        "volume_threshold": 1500,
        "difficulty_threshold": 30,
        "npath_threshold": 400,
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
        "weighted_threshold": 80,
        "volume_threshold": 3000,
        "difficulty_threshold": 50,
        "npath_threshold": 1000,
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
        "volume_threshold": 500,
        "difficulty_threshold": 20,
        "npath_threshold": 100,
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

# Scoped waivers keep exceptional findings visible without weakening global
# thresholds. Prefer a local allow_up_to ceiling over an unbounded waiver.
# [[waivers]]
# id = "parser-npath"
# path = "src/parser/**"
# rule = "npath"
# allow_up_to = 1200
# reason = "Parser branch shape mirrors grammar alternatives."
# expires = "2026-09-01"

[rules.complexity]
enabled = true
cyclomatic_threshold = {p["cyclomatic_threshold"]}       # fail if any function CCX exceeds this
cognitive_threshold = {p["cognitive_threshold"]}        # fail if any function CogC exceeds this
weighted_threshold = {p["weighted_threshold"]}         # fail if any class WMC exceeds this
severity = "error"

[rules.halstead]
enabled = true
volume_threshold = {p["volume_threshold"]}         # fail if any function V exceeds this
difficulty_threshold = {p["difficulty_threshold"]}        # fail if any function D exceeds this
severity = "error"

[rules.npath]
enabled = true
npath_threshold = {p["npath_threshold"]}         # fail if any function NPath exceeds this
severity = "error"

[rules.hotspots]
enabled = true
since = "{p["hotspots_since"]}"
min_commits = {p["hotspots_min_commits"]}
fail_on_quadrant = [{quadrant_list}]
severity = "error"

[rules.packages]
enabled = true
# languages = ["python"]        # optional: restrict to a subset of slop's supported languages
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
