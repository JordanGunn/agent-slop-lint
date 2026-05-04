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

from slop._compat import (
    canonical_rule_name,
    collect_prefix_overrides,
    format_deprecation_block,
    migrate_legacy_rule_tables,
)
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
    "structural.complexity": {
        "enabled": True,
        "severity": "error",
        "cyclomatic_threshold": 10,
        "cognitive_threshold": 15,
        "npath_threshold": 400,
    },
    "structural.class.complexity": {
        "enabled": True,
        "severity": "error",
        "threshold": 40,
    },
    "structural.class.coupling": {
        "enabled": True,
        "severity": "error",
        "threshold": 8,
    },
    "structural.class.inheritance.depth": {
        "enabled": True,
        "severity": "error",
        "threshold": 4,
    },
    "structural.class.inheritance.children": {
        "enabled": True,
        "severity": "error",
        "threshold": 10,
    },
    "structural.hotspots": {
        "enabled": True,
        "severity": "error",
        "since": "14 days ago",
        "min_commits": 2,
        "fail_on_quadrant": ["hotspot"],
    },
    "structural.packages": {
        "enabled": True,
        "severity": "warning",
        "languages": [],
        "max_distance": 0.7,
        "fail_on_zone": ["pain"],
    },
    "structural.deps": {
        "enabled": True,
        "severity": "error",
        "fail_on_cycles": True,
    },
    "structural.local_imports": {
        "enabled": True,
        "severity": "warning",
        "threshold": 0,
    },
    "structural.redundancy": {
        "enabled": True,
        "severity": "warning",
        "min_shared": 3,
        "min_score": 0.5,
    },
    "structural.types.sentinels": {
        "enabled": True,
        "severity": "warning",
        "max_cardinality": 8,
        "require_str_annotation": True,
    },
    "structural.types.hidden_mutators": {
        "enabled": True,
        "severity": "warning",
        "require_type_annotation": True,
        "min_mutations": 1,
    },
    "structural.types.escape_hatches": {
        "enabled": True,
        "severity": "warning",
        "threshold": 0.30,
        "min_annotations": 5,
    },
    "structural.duplication": {
        "enabled": True,
        "severity": "warning",
        "threshold": 0.05,
        "min_leaf_nodes": 10,
        "min_cluster_size": 2,
    },
    "structural.god_module": {
        "enabled": True,
        "severity": "warning",
        "threshold": 20,
    },
    "structural.orphans": {
        "enabled": False,
        "severity": "warning",
        "min_confidence": "high",
    },
    "information.volume": {
        "enabled": True,
        "severity": "error",
        "threshold": 1500,
        "token_weight_alpha": 0.0,
    },
    "information.difficulty": {
        "enabled": True,
        "severity": "error",
        "threshold": 30,
    },
    "information.magic_literals": {
        "enabled": True,
        "severity": "warning",
        "threshold": 3,
    },
    "information.section_comments": {
        "enabled": True,
        "severity": "warning",
        "threshold": 2,
    },
    "lexical.stutter": {
        "enabled": True,
        "severity": "warning",
        "min_overlap_tokens": 2,
    },
    "lexical.verbosity": {
        "enabled": True,
        "severity": "warning",
        "max_mean_tokens": 3.0,
        "min_identifiers": 5,
    },
    "lexical.tersity": {
        "enabled": True,
        "severity": "warning",
        "max_density": 0.50,
        "max_len": 2,
        "min_identifiers": 5,
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


def _build_rule_configs(
    raw_rules: dict[str, Any],
) -> tuple[dict[str, RuleConfig], list[str]]:
    """Build RuleConfig dict by merging user config over defaults.

    Translates legacy ``[rules.<category>]`` tables to the canonical
    taxonomy via ``slop._compat`` and returns any deprecation lines for
    the caller to surface. Intermediate prefix tables (``[rules.structural]``,
    ``[rules.structural.class]``) propagate their ``enabled`` / ``severity``
    scalars to every nested canonical category; more specific tables win.
    """
    canonical_keys = set(DEFAULT_RULE_CONFIGS.keys())
    migrated, deprecations = migrate_legacy_rule_tables(raw_rules, canonical_keys)
    prefix_overrides = collect_prefix_overrides(raw_rules, canonical_keys)
    result: dict[str, RuleConfig] = {}
    for category, defaults in DEFAULT_RULE_CONFIGS.items():
        layered: dict[str, Any] = {}
        parts = category.split(".")
        for i in range(1, len(parts)):
            ancestor = ".".join(parts[:i])
            override = prefix_overrides.get(ancestor)
            if override:
                layered.update(override)
        user_overrides = migrated.get(category, {})
        if isinstance(user_overrides, dict):
            layered.update(user_overrides)
        result[category] = _merge_rule_config(defaults, layered)
    return result, deprecations


def _build_waivers(raw_waivers: Any) -> tuple[list[WaiverConfig], list[str]]:
    """Build and validate top-level waiver configuration.

    Returns the waivers and any deprecation lines describing legacy rule
    names that were translated to canonical form.
    """
    if raw_waivers is None:
        return [], []
    if not isinstance(raw_waivers, list):
        raise ValueError("waivers must be an array of tables")

    waivers: list[WaiverConfig] = []
    deprecations: list[str] = []
    seen_ids: set[str] = set()
    for i, raw in enumerate(raw_waivers, start=1):
        waiver, dep = _build_waiver(raw, i, seen_ids)
        waivers.append(waiver)
        if dep is not None:
            deprecations.append(dep)
    return waivers, deprecations


def _build_waiver(
    raw: Any, index: int, seen_ids: set[str]
) -> tuple[WaiverConfig, str | None]:
    """Build one waiver from a TOML table.

    If the waiver's ``rule`` field is a legacy name (no glob), it is
    translated to the canonical form and a deprecation line is returned.
    Glob patterns are passed through unchanged because rule patterns can
    legitimately be wildcards (e.g. ``structural.*``).
    """
    if not isinstance(raw, dict):
        raise ValueError(f"waiver #{index} must be a table")

    waiver_id = _required_string(raw, "id", f"waiver #{index}")
    if waiver_id in seen_ids:
        raise ValueError(f"duplicate waiver id: {waiver_id}")
    seen_ids.add(waiver_id)

    rule = _required_string(raw, "rule", f"waiver {waiver_id}")
    deprecation: str | None = None
    if not any(c in rule for c in ("*", "?", "[")):
        canonical, was_legacy = canonical_rule_name(rule)
        if was_legacy:
            deprecation = (
                f"  waiver {waiver_id}: rule = \"{rule}\" -> \"{canonical}\""
            )
            rule = canonical

    waiver = WaiverConfig(
        id=waiver_id,
        path=_required_string(raw, "path", f"waiver {waiver_id}"),
        rule=rule,
        reason=_required_string(raw, "reason", f"waiver {waiver_id}"),
        allow_up_to=_optional_number(raw, "allow_up_to", f"waiver {waiver_id}"),
        expires=_optional_iso_date(raw, "expires", f"waiver {waiver_id}"),
    )
    return waiver, deprecation


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


def _read_raw_config(
    config_path: str | None, root: str | None,
) -> tuple[Path | None, dict[str, Any]]:
    """Locate and read the raw config dict according to source priority.

    Priority 1 is an explicit ``--config`` path; otherwise an upward walk
    from ``root`` (or CWD) looks for ``.slop.toml`` then ``pyproject.toml``
    with a ``[tool.slop]`` table.
    """
    if config_path:
        config_file = Path(config_path)
        if not config_file.is_file():
            raise FileNotFoundError(f"Config file not found: {config_file}")
        raw = _read_toml(config_file)
        if config_file.name == "pyproject.toml":
            raw = raw.get("tool", {}).get("slop", {})
        return config_file.resolve(), raw
    search_root = Path(root) if root else Path.cwd()
    return _discover_config(search_root)


def _resolve_config_root(
    raw_root: Any, root: str | None, discovered_config: Path | None,
) -> str:
    """Resolve the effective scan root from config + caller-supplied hint.

    Precedence: config's ``root`` (resolved against the config file's
    directory when relative) wins when present; otherwise the caller's
    ``root`` argument; final fallback is ``"."``. CLI ``--root`` is
    applied by the caller after ``load_config`` returns.
    """
    if raw_root is not None:
        raw_root_path = Path(raw_root)
        if raw_root_path.is_absolute() or discovered_config is None:
            return str(raw_root_path)
        return str((discovered_config.parent / raw_root_path).resolve())
    if root is not None:
        return root
    return "."


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
    discovered_config, raw = _read_raw_config(config_path, root)

    raw_root = raw.get("root")
    languages = raw.get("languages", [])
    exclude = raw.get("exclude", [])
    waivers, waiver_deprecations = _build_waivers(raw.get("waivers"))
    config_root = _resolve_config_root(raw_root, root, discovered_config)

    raw_rules = raw.get("rules", {})
    if not isinstance(raw_rules, dict):
        raw_rules = {}
    rule_configs, rule_deprecations = _build_rule_configs(raw_rules)

    deprecations = rule_deprecations + waiver_deprecations
    if deprecations:
        print(format_deprecation_block(deprecations), file=sys.stderr)

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
    profile_cfg = PROFILES[profile]
    quadrant_list = ", ".join(f'"{quadrant}"' for quadrant in profile_cfg["hotspots_fail_on_quadrant"])
    orphans_enabled = "true" if profile_cfg["orphans_enabled"] else "false"
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
# rule = "structural.complexity.npath"
# allow_up_to = 1200
# reason = "Parser branch shape mirrors grammar alternatives."
# expires = "2026-09-01"

[rules.structural.complexity]
enabled = true
cyclomatic_threshold = {profile_cfg["cyclomatic_threshold"]}       # fail if any function CCX exceeds this
cognitive_threshold = {profile_cfg["cognitive_threshold"]}        # fail if any function CogC exceeds this
npath_threshold = {profile_cfg["npath_threshold"]}         # fail if any function NPath exceeds this
severity = "error"

[rules.structural.class.complexity]
enabled = true
threshold = {profile_cfg["weighted_threshold"]}              # fail if any class WMC exceeds this
severity = "error"

[rules.structural.class.coupling]
enabled = true
threshold = {profile_cfg["coupling_threshold"]}
severity = "error"

[rules.structural.class.inheritance.depth]
enabled = true
threshold = {profile_cfg["inheritance_depth_threshold"]}
severity = "error"

[rules.structural.class.inheritance.children]
enabled = true
threshold = {profile_cfg["inheritance_children_threshold"]}
severity = "error"

[rules.structural.hotspots]
enabled = true
since = "{profile_cfg["hotspots_since"]}"
min_commits = {profile_cfg["hotspots_min_commits"]}
fail_on_quadrant = [{quadrant_list}]
severity = "error"

[rules.structural.packages]
enabled = true
# languages = ["python"]        # optional: restrict to a subset of slop's supported languages
max_distance = {profile_cfg["max_distance"]}
fail_on_zone = ["pain"]
severity = "{profile_cfg["packages_severity"]}"

[rules.structural.deps]
enabled = true
fail_on_cycles = true
severity = "error"

[rules.structural.local_imports]
enabled = true
# threshold = 0     # allow up to N local imports per file before flagging
severity = "warning"
# ── Python: local imports are a genuine idiom in three common situations ──────
# 1. Optional / heavy dependencies deferred until the feature is actually used:
#    [[waivers]]
#    id = "local-imports-optional-dep"
#    path = "src/your_package/**"
#    rule = "structural.local_imports"
#    reason = "Heavy optional dependency deferred to avoid import-time cost or crash when wheels are absent."
#
# 2. CLI subcommand handlers deferring imports for startup speed:
#    [[waivers]]
#    id = "local-imports-cli-startup"
#    path = "src/your_package/cli.py"
#    rule = "structural.local_imports"
#    reason = "CLI command handlers defer imports so users only pay the cost for the subcommand they invoke."
#
# 3. Test functions that import inside the body for monkeypatching:
#    [[waivers]]
#    id = "local-imports-test-monkeypatch"
#    path = "tests/**"
#    rule = "structural.local_imports"
#    reason = "Import inside function body is required so the test can monkeypatch the module before the code under test runs."
# ─────────────────────────────────────────────────────────────────────────────

[rules.structural.redundancy]
enabled = true
min_shared = 3      # minimum shared non-trivial callees between two sibling functions
min_score = 0.5     # minimum overlap ratio (shared / max callee count)
severity = "warning"

[rules.structural.types.sentinels]
enabled = true
max_cardinality = 8   # flag sentinel str params with ≤ 8 distinct call-site values
require_str_annotation = true
severity = "warning"

[rules.structural.types.hidden_mutators]
enabled = true
require_type_annotation = true   # only flag params with explicit collection types
min_mutations = 1
severity = "warning"

[rules.structural.types.escape_hatches]
enabled = true
threshold = 0.30    # flag files where > 30% of annotations use escape-hatch types
min_annotations = 5
severity = "warning"

[rules.structural.duplication]
enabled = true
threshold = 0.05    # flag when > 5% of functions are Type-2 clones
min_leaf_nodes = 10 # ignore trivially short functions
min_cluster_size = 2
severity = "warning"

[rules.structural.god_module]
enabled = true
threshold = 20      # flag files with more than this many top-level definitions
severity = "warning"

[rules.structural.orphans]
enabled = {orphans_enabled}
min_confidence = "high"
severity = "warning"

[rules.information.volume]
enabled = true
threshold = {profile_cfg["volume_threshold"]}         # fail if any function V exceeds this
# token_weight_alpha = 0.0   # > 0 tightens threshold for terse-identifier functions
severity = "error"

[rules.information.difficulty]
enabled = true
threshold = {profile_cfg["difficulty_threshold"]}        # fail if any function D exceeds this
severity = "error"

[rules.information.magic_literals]
enabled = true
threshold = 3       # flag functions with > 3 distinct non-trivial numeric literals
severity = "warning"

[rules.information.section_comments]
enabled = true
threshold = 2       # flag functions with more than this many section-divider comments
severity = "warning"

[rules.lexical.stutter]
enabled = true
min_overlap_tokens = 2   # flag identifiers repeating \u2265 N tokens from enclosing scope
severity = "warning"

[rules.lexical.verbosity]
enabled = true
max_mean_tokens = 3.0   # flag functions where mean word-tokens-per-identifier > this
min_identifiers = 5     # skip functions with fewer identifiers than this
severity = "warning"

[rules.lexical.tersity]
enabled = true
max_density = 0.50      # flag functions where > 50% of identifiers are ≤ max_len chars
max_len = 2
min_identifiers = 5
# allow_list = ["i", "j", "k", "x", "y", "z", "ok", "n"]   # conventional short names
severity = "warning"
'''
