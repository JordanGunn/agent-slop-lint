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

from slop.config.config import Config
from slop.linter.rule import Rule
from slop.linter.tags import Tag

# Valid scope keys for [ignore] / [rules.<rule>.ignore] — each maps 1:1 to a
# finding scope, so every key suppresses exactly what its name says.
_IGNORE_SCOPES: tuple[str, ...] = ("functions", "classes", "modules", "packages")

# ---------------------------------------------------------------------------
# TOML structure handling
# ---------------------------------------------------------------------------

_PREFIX_PROPAGATABLE_KEYS: tuple[str, ...] = ("enabled", "severity")


def _flatten_canonical_tables(
    raw_rules: dict, canonical_keys: set[str],
) -> dict[str, dict]:
    """Collapse the TOML-nested rule tree into flat dotted keys.

    TOML parses ``[rules.hotspots]`` as
    ``raw["rules"]["hotspots"] = {...}`` and ``[rules.class.coupling]``
    as ``raw["rules"]["class"]["coupling"] = {...}``. This walks the
    nested dict and emits each known canonical category back as a flat
    ``"hotspots" -> {...}`` mapping so the merge step can work
    uniformly. Unknown nested paths are ignored.
    """
    flat: dict[str, dict] = {}

    def _walk(node, path: tuple[str, ...]) -> None:
        if not isinstance(node, dict):
            return
        dotted = ".".join(path) if path else ""
        if dotted in canonical_keys:
            flat[dotted] = node
            return
        for key, value in node.items():
            _walk(value, path + (key,))

    _walk(raw_rules, ())
    return flat


def _collect_prefix_overrides(
    raw_rules: dict, canonical_keys: set[str],
) -> dict[str, dict]:
    """Collect intermediate prefix tables that propagate to nested rules.

    A prefix table sits at a non-canonical dotted path (``class``,
    ``complexity``) and contains scalar ``enabled`` or ``severity``
    values. Those values propagate to every canonical category whose
    dotted name starts with the prefix, letting users disable a whole
    suite (``[rules.class] enabled = false``) or downgrade an entire
    group's severity in one place.
    """
    overrides: dict[str, dict] = {}

    def _walk(node, path: tuple[str, ...]) -> None:
        if not isinstance(node, dict):
            return
        dotted = ".".join(path) if path else ""
        if dotted in canonical_keys:
            return
        if path:
            scalars = {
                k: node[k]
                for k in _PREFIX_PROPAGATABLE_KEYS
                if k in node and not isinstance(node[k], dict)
            }
            if scalars:
                overrides[dotted] = scalars
        for key, value in node.items():
            _walk(value, path + (key,))

    _walk(raw_rules, ())
    return overrides

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
    # --- complexity family (multi-scope, scope-first design) ---
    # Each rule supports multiple scopes via per-scope thresholds. A
    # missing scope key in `thresholds` = rule skips that scope.
    Tag.CYCLOMATIC.key: {
        "enabled": True,
        "severity": "error",
        "thresholds": {"function": 10, "class": 40},
    },
    Tag.COGNITIVE.key: {
        "enabled": True,
        "severity": "error",
        # Class-scope threshold is slop calibration (no published value
        # for the aggregated form; Campbell 2018 only defined function).
        "thresholds": {"function": 15, "class": 60},
    },
    Tag.COMBINATORIAL.key: {
        "enabled": True,
        "severity": "error",
        # Class-scope threshold is slop calibration (Nejmeh 1988 only
        # defined function-scope NPath).
        "thresholds": {"function": 400, "class": 1600},
    },
    Tag.VOLUME.key: {
        "enabled": True,
        "severity": "error",
        # Class-scope threshold is slop calibration (Halstead 1977
        # defined function-scope V; sum is additive, so aggregation is
        # mathematically defensible but no published threshold).
        "thresholds": {"function": 1500, "class": 6000},
    },
    Tag.DENSITY.key: {
        "enabled": True,
        "severity": "error",
        # Function-scope only — Halstead D is a density ratio and
        # non-additive across methods. No class-scope variant.
        "thresholds": {"function": 30},
    },
    # --- CK class metrics ---
    Tag.COUPLING.key: {
        "enabled": True,
        "severity": "error",
        "thresholds": {"class": 8},
    },
    Tag.DEPTH.key: {
        "enabled": True,
        "severity": "error",
        "thresholds": {"class": 4},
    },
    Tag.CHILDREN.key: {
        "enabled": True,
        "severity": "error",
        "thresholds": {"class": 10},
    },
    # --- Standalone scope-determined rules ---
    Tag.MAGIC_LITERALS.key: {
        "enabled": True,
        "severity": "warning",
        "thresholds": {"function": 3},
    },
    Tag.GOD_MODULE.key: {
        "enabled": True,
        "severity": "warning",
        "thresholds": {"module": 20},
    },
    Tag.ESCAPE_HATCHES.key: {
        "enabled": True,
        "severity": "warning",
        "thresholds": {"module": 0.30},
        "min_annotations": 5,
    },
    Tag.HIDDEN_MUTATORS.key: {
        "enabled": True,
        "severity": "warning",
        "thresholds": {"function": 1},
        "require_type_annotation": True,
    },
    Tag.SENTINELS.key: {
        "enabled": True,
        "severity": "warning",
        "thresholds": {"parameter": 8},
        "require_str_annotation": True,
    },
    Tag.RIGIDITY.key: {
        "enabled": True,
        "severity": "warning",
        "thresholds": {"package": 0.7},
        "languages": [],
    },
    Tag.USELESSNESS.key: {
        "enabled": True,
        "severity": "warning",
        "thresholds": {"package": 0.7},
        "languages": [],
    },
    # --- Cross-cutting (graph or whole-repo; exempt from scope prefix) ---
    Tag.HOTSPOTS.key: {
        "enabled": True,
        "severity": "error",
        "since": "14 days ago",
        "min_commits": 2,
        "fail_on_quadrant": ["hotspot"],
    },
    Tag.DEPS.key: {
        "enabled": True,
        "severity": "error",
        "fail_on_cycles": True,
    },
    Tag.ORPHANS.key: {
        "enabled": False,
        "severity": "warning",
        "min_confidence": "high",
    },
    Tag.REDUNDANCY.key: {
        "enabled": True,
        "severity": "warning",
        "min_shared": 3,
        "min_score": 0.5,
    },
    Tag.DUPLICATION.key: {
        "enabled": True,
        "severity": "warning",
        "threshold": 0.05,
        "min_leaf_nodes": 10,
        "min_cluster_size": 2,
    },
    Tag.STUTTER.key: {
        "enabled": True,
        "severity": "warning",
        "min_overlap_tokens": 2,
        "check_packages": True,
        "check_modules": True,
        "check_classes": True,
        "check_functions": True,
    },
    Tag.VERBOSITY.key: {
        "enabled": True,
        "severity": "warning",
        "max_tokens": 3,
        "check_classes": True,
    },
    Tag.HAMMERS.key: {
        "enabled": True,
        "severity": "warning",
    },
    Tag.SPRAWL.key: {
        "enabled": True,
        "severity": "warning",
        "min_alphabet": 3,
        "min_concept_extent": 2,
        "min_concept_intent": 2,
    },
    Tag.IMPOSTERS.key: {
        "enabled": True,
        "severity": "warning",
        "min_cluster": 3,
        "exempt_names": ["self", "cls"],
    },
    Tag.SLACKERS.key: {
        "enabled": True,
        "severity": "warning",
        "min_cluster": 3,
        "exempt_names": ["self", "cls"],
        "max_coverage": 0.30,
    },
    Tag.CONFUSION.key: {
        "enabled": True,
        "severity": "warning",
        "min_functions": 5,
        "min_islands": 2,
        "min_shared": 3,
        "min_score": 0.5,
        "min_island_size": 2,
        "min_cluster_size": 3,
        "exempt_names": ["self", "cls"],
    },
    Tag.RUNTS.key: {
        "enabled": True,
        "severity": "warning",
        "max_init_lines": 5,
    },
    # --- Instrumentation (observation, not verdict; never fails a build) ---
    Tag.VOCABULARY.key: {
        "enabled": True,
        "severity": "info",
        "top_tokens": 15,
        "package_min_distinct": 40,
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
) -> Rule:
    """Merge a default rule config dict with user overrides into a Rule.

    The nested ``thresholds`` dict is deep-merged so a user override
    of one scope (e.g., ``thresholds = {class = 50}``) keeps the
    other scope defaults intact rather than wiping them.
    """
    merged: dict[str, Any] = dict(defaults)
    for k, v in overrides.items():
        if (
            k == "thresholds"
            and isinstance(v, dict)
            and isinstance(merged.get("thresholds"), dict)
        ):
            merged_thresholds = dict(merged["thresholds"])
            merged_thresholds.update(v)
            merged["thresholds"] = merged_thresholds
        else:
            merged[k] = v
    enabled = merged.pop("enabled", True)
    severity = merged.pop("severity", "error")
    return Rule(enabled=enabled, severity=severity, params=merged)


def _build_rule_configs(
    raw_rules: dict[str, Any],
) -> dict[str, Rule]:
    """Build Rule dict by merging user config over defaults.

    Intermediate prefix tables (``[rules.class]``,
    ``[rules.complexity]``) propagate their ``enabled`` / ``severity``
    scalars to every nested canonical category; more specific tables win.
    """
    canonical_keys = set(DEFAULT_RULE_CONFIGS.keys())
    flat = _flatten_canonical_tables(raw_rules, canonical_keys)
    prefix_overrides = _collect_prefix_overrides(raw_rules, canonical_keys)
    result: dict[str, Rule] = {}
    for category, defaults in DEFAULT_RULE_CONFIGS.items():
        layered: dict[str, Any] = {}
        parts = category.split(".")
        for i in range(1, len(parts)):
            ancestor = ".".join(parts[:i])
            override = prefix_overrides.get(ancestor)
            if override:
                layered.update(override)
        user_overrides = flat.get(category, {})
        if isinstance(user_overrides, dict):
            layered.update(user_overrides)
        rule = _merge_rule_config(defaults, layered)
        if "ignore" in rule.params:
            rule.params["ignore"] = _build_ignore(
                rule.params["ignore"], label=f"[rules.{category}.ignore]",
            )
        result[category] = rule
    return result


def _build_ignore(raw_ignore: Any, label: str = "[ignore]") -> dict[str, list[str]]:
    """Validate a scope-keyed ignore table: scope -> list of declared names.

    Only the four scopes in ``_IGNORE_SCOPES`` are accepted; an unknown
    key (a typo, or a tag the mechanism can't honour like ``any``) raises
    loudly rather than silently doing nothing. Used for both the global
    ``[ignore]`` table and per-rule ``[rules.<rule>.ignore]`` tables.
    """
    if raw_ignore is None:
        return {}
    if not isinstance(raw_ignore, dict):
        raise ValueError(f"{label} must be a table of scope -> name list")
    out: dict[str, list[str]] = {}
    for scope, names in raw_ignore.items():
        if scope not in _IGNORE_SCOPES:
            raise ValueError(
                f"{label} unknown scope '{scope}'; valid scopes are "
                f"{', '.join(_IGNORE_SCOPES)}"
            )
        if not isinstance(names, list) or not all(isinstance(n, str) for n in names):
            raise ValueError(f"{label}.{scope} must be a list of strings")
        out[scope] = list(names)
    return out


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
):
    """Load slop configuration from TOML files with fallback to defaults."""
    discovered_config, raw = _read_raw_config(config_path, root)

    raw_root = raw.get("root")
    languages = raw.get("languages", [])
    exclude = raw.get("exclude", [])
    ignore = _build_ignore(raw.get("ignore"))
    config_root = _resolve_config_root(raw_root, root, discovered_config)

    raw_rules = raw.get("rules", {})
    if not isinstance(raw_rules, dict):
        raw_rules = {}
    rule_configs = _build_rule_configs(raw_rules)

    return Config(
        root=config_root,
        languages=languages,
        exclude=exclude,
        ignore=ignore,
        rules=rule_configs,
        config_path=discovered_config,
    )

