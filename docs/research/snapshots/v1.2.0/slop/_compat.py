"""Centralised compatibility shim for the 0.9.0 / 1.1.0 rule-name migrations.

Every legacy → canonical translation lives in this module so the rest of the
codebase only ever speaks the canonical taxonomy (``structural.*``,
``information.*``, ``lexical.*``). One pass at config-load time normalises
raw TOML tables and waiver references; one pass at filter-resolution time
normalises CLI arguments. Both passes funnel through the constants below.

Deprecation contract
--------------------
* Deprecated in: 0.9.0
* Scheduled removal: 1.1.0

When any legacy name is encountered the consumer must call
``record_deprecation`` so a single consolidated warning block is rendered
to stderr at the end of config load.
"""

from __future__ import annotations

DEPRECATED_IN = "0.9.0"
REMOVED_IN = "1.1.0"


# --- Rule-name aliases --------------------------------------------------------
# Keys are legacy fully-qualified rule names; values are the new canonical
# rule names. Used by waivers, ``slop check <rule>``, and any other place
# that resolves a single rule by name.
LEGACY_RULE_NAMES: dict[str, str] = {
    "complexity.cyclomatic": "structural.complexity.cyclomatic",
    "complexity.cognitive": "structural.complexity.cognitive",
    "complexity.weighted": "structural.class.complexity",
    "npath": "structural.complexity.npath",
    "hotspots": "structural.hotspots",
    "packages": "structural.packages",
    "deps": "structural.deps",
    "orphans": "structural.orphans",
    "class.coupling": "structural.class.coupling",
    "class.inheritance.depth": "structural.class.inheritance.depth",
    "class.inheritance.children": "structural.class.inheritance.children",
    "halstead.volume": "information.volume",
    "halstead.difficulty": "information.difficulty",
    # v1.1.0 names that didn't ship; collapsed in v1.2.0
    "composition.affix_polymorphism": "lexical.sprawl",
    "composition.first_parameter_drift": "lexical.imposters",
    "lexical.name_verbosity": "lexical.verbosity",
    "lexical.numbered_variants": "lexical.cowards",
    "lexical.weasel_words": "lexical.hammers",
    "lexical.type_tag_suffixes": "lexical.tautology",
    # v1.1.0 stutter split; v1.2.0 unified back into a single
    # hierarchy-aware rule. All three sub-rules map to the unified
    # name; the new rule's per-level toggles preserve dial-down.
    "lexical.stutter.namespaces": "lexical.stutter",
    "lexical.stutter.callers": "lexical.stutter",
    "lexical.stutter.identifiers": "lexical.stutter",
    # Pre-1.0 names (still translated; pre-existing).
    "lexical.identifier_token_count": "lexical.verbosity",
    "lexical.short_identifier_density": "lexical.tersity",
}


# Rules removed entirely in v1.2.0. Stored as
# ``rule_name -> removal_reason``. The compat layer detects
# references to these and emits "removed in v1.2.0" stderr
# warnings rather than translating to a successor.
REMOVED_RULES: dict[str, str] = {
    "lexical.tersity": (
        "removed in v1.2.0 — body-identifier-mean rules were style "
        "measurements that didn't validate slop's structural-debt thesis."
    ),
    "lexical.boilerplate_docstrings": (
        "removed in v1.2.0 — docstring-quality smells are easy fixes "
        "that don't validate slop's structural-debt thesis."
    ),
    "lexical.identifier_singletons": (
        "removed in v1.2.0 — overlapped weakly with structural concerns; "
        "weaker than other v1.2.0 rules in the same space."
    ),
}


# --- Category aliases ---------------------------------------------------------
# Legacy CLI categories (``slop check complexity``) translate to one or more
# new categories. A single legacy category can fan out to multiple new ones
# (``halstead`` covers two ``information.*`` rules; ``complexity`` covers
# both ``structural.complexity`` and the WMC rule under ``structural.class``).
LEGACY_CATEGORIES: dict[str, tuple[str, ...]] = {
    "complexity": ("structural.complexity", "structural.class.complexity"),
    "halstead": ("information.volume", "information.difficulty"),
    "npath": ("structural.complexity.npath",),
    "hotspots": ("structural.hotspots",),
    "packages": ("structural.packages",),
    "deps": ("structural.deps",),
    "orphans": ("structural.orphans",),
    "class": (
        "structural.class.complexity",
        "structural.class.coupling",
        "structural.class.inheritance.depth",
        "structural.class.inheritance.children",
    ),
}


# --- TOML table migrations ----------------------------------------------------
# Each entry describes how one legacy ``[rules.<table>]`` table maps onto
# zero or more new tables. ``key_map`` lists the keys to copy; values are
# the canonical key names (which may equal the legacy key). Keys not listed
# are dropped silently — any meaningful key must appear here so we do not
# lose user intent.
LEGACY_TABLE_MIGRATIONS: list[tuple[str, str, dict[str, str]]] = [
    ("complexity", "structural.complexity", {
        "enabled": "enabled",
        "severity": "severity",
        "cyclomatic_threshold": "cyclomatic_threshold",
        "cognitive_threshold": "cognitive_threshold",
    }),
    ("complexity", "structural.class.complexity", {
        "weighted_threshold": "threshold",
    }),
    ("npath", "structural.complexity", {
        "enabled": "enabled",
        "severity": "severity",
        "npath_threshold": "npath_threshold",
    }),
    ("halstead", "information.volume", {
        "enabled": "enabled",
        "severity": "severity",
        "volume_threshold": "threshold",
    }),
    ("halstead", "information.difficulty", {
        "enabled": "enabled",
        "severity": "severity",
        "difficulty_threshold": "threshold",
    }),
    ("hotspots", "structural.hotspots", {
        "enabled": "enabled", "severity": "severity",
        "since": "since", "min_commits": "min_commits",
        "fail_on_quadrant": "fail_on_quadrant",
    }),
    ("packages", "structural.packages", {
        "enabled": "enabled", "severity": "severity",
        "languages": "languages", "max_distance": "max_distance",
        "fail_on_zone": "fail_on_zone",
    }),
    ("deps", "structural.deps", {
        "enabled": "enabled", "severity": "severity",
        "fail_on_cycles": "fail_on_cycles",
    }),
    ("orphans", "structural.orphans", {
        "enabled": "enabled", "severity": "severity",
        "min_confidence": "min_confidence",
    }),
    ("class", "structural.class.coupling", {
        "enabled": "enabled", "severity": "severity",
        "coupling_threshold": "threshold",
    }),
    ("class", "structural.class.inheritance.depth", {
        "inheritance_depth_threshold": "threshold",
    }),
    ("class", "structural.class.inheritance.children", {
        "inheritance_children_threshold": "threshold",
    }),
    ("lexical", "lexical.verbosity", {
        "min_mean_tokens": "max_mean_tokens",
    }),
    ("lexical", "lexical.tersity", {
        "max_density": "max_density",
    }),
]


def canonical_rule_name(name: str) -> tuple[str, bool]:
    """Translate a possibly-legacy rule name to its canonical form.

    Returns ``(canonical_name, was_legacy)``. If the name is already
    canonical (or unknown), returns it unchanged with ``False``.
    """
    new = LEGACY_RULE_NAMES.get(name)
    if new is None:
        return name, False
    return new, True


def canonical_categories(name: str) -> tuple[tuple[str, ...], bool]:
    """Translate a possibly-legacy category to its canonical category set.

    Returns ``(categories, was_legacy)``. Unknown names pass through
    unchanged as a single-element tuple with ``was_legacy=False``.
    """
    new = LEGACY_CATEGORIES.get(name)
    if new is None:
        return (name,), False
    return new, True


PREFIX_PROPAGATABLE_KEYS: tuple[str, ...] = ("enabled", "severity")


def collect_prefix_overrides(
    raw_rules: dict, canonical_keys: set[str],
) -> dict[str, dict]:
    """Collect intermediate prefix tables that propagate to nested rules.

    A prefix table sits at a non-canonical dotted path (``structural``,
    ``structural.class``) and contains scalar ``enabled`` or ``severity``
    values. Those values propagate to every canonical category whose
    dotted name starts with the prefix, letting users disable a whole
    suite (``[rules.structural] enabled = false``) or downgrade an entire
    group's severity in one place. Other keys at intermediate levels are
    ignored because they have no consistent meaning across rules.

    Returns ``{prefix -> {key: value}}`` keyed by dotted prefix path,
    including only ``PREFIX_PROPAGATABLE_KEYS``.
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
                for k in PREFIX_PROPAGATABLE_KEYS
                if k in node and not isinstance(node[k], dict)
            }
            if scalars:
                overrides[dotted] = scalars
        for key, value in node.items():
            _walk(value, path + (key,))

    _walk(raw_rules, ())
    return overrides


def _flatten_canonical_tables(
    raw_rules: dict, canonical_keys: set[str],
) -> dict[str, dict]:
    """Collapse the TOML-nested rule tree into flat dotted keys.

    TOML parses ``[rules.structural.hotspots]`` as
    ``raw["rules"]["structural"]["hotspots"] = {...}``. This walks the
    nested dict and emits each known canonical category back as a flat
    ``"structural.hotspots" -> {...}`` mapping so the merge step can
    work uniformly. Unknown nested paths are ignored.
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


def _is_leaf_legacy_table(table: dict) -> bool:
    """A leaf legacy table is non-empty and has at least one scalar value.

    Filters out the case where ``raw_rules["structural"]`` looks like a
    dict but is actually the parent of nested canonical tables.
    """
    if not table:
        return False
    return any(not isinstance(v, dict) for v in table.values())


def _apply_one_legacy_table(
    legacy_table: dict, target: dict, key_map: dict[str, str],
) -> bool:
    """Copy mapped keys from a legacy table into a target dict.

    Returns True if any key was copied (so the caller can record the
    translation as a deprecation).
    """
    copied = False
    for src_key, dst_key in key_map.items():
        if src_key in legacy_table:
            target[dst_key] = legacy_table[src_key]
            copied = True
    return copied


def _collect_legacy_derivations(
    raw_rules: dict,
) -> tuple[dict[str, dict], list[str]]:
    """Walk LEGACY_TABLE_MIGRATIONS and translate each legacy table found."""
    derived: dict[str, dict] = {}
    deprecations: list[str] = []
    for legacy_key, target_key, key_map in LEGACY_TABLE_MIGRATIONS:
        legacy_table = raw_rules.get(legacy_key)
        if not isinstance(legacy_table, dict) or not _is_leaf_legacy_table(legacy_table):
            continue
        target = derived.setdefault(target_key, {})
        if _apply_one_legacy_table(legacy_table, target, key_map):
            deprecations.append(f"  [rules.{legacy_key}] -> [rules.{target_key}]")
    return derived, deprecations


def _migrate_v110_stutter_subrules(
    raw_rules: dict,
) -> tuple[dict, list[str]]:
    """Map v1.1.0 stutter sub-rule tables to the v1.2.0 unified rule.

    v1.1.0 split ``lexical.stutter`` into three sub-rules
    (``namespaces`` / ``callers`` / ``identifiers``); v1.2.0 unified
    them back into a single hierarchy-aware ``lexical.stutter`` rule
    with per-level toggle parameters. Convert any
    ``[rules.lexical.stutter.<level>]`` table into the corresponding
    ``check_<level>`` parameter on the unified rule.

    The v1.1.0 release was held and never tagged, so any user with
    these sub-rule tables predates the v1.2.0 ship — but the dogfood
    config and tests reference them, hence the migration.
    """
    derived: dict = {}
    deprecations: list[str] = []
    lexical = raw_rules.get("lexical")
    if not isinstance(lexical, dict):
        return derived, deprecations
    stutter = lexical.get("stutter")
    if not isinstance(stutter, dict):
        return derived, deprecations
    # Legacy sub-tables present?
    sub_to_param = {
        "namespaces": "check_modules",
        "callers": "check_classes",
        "identifiers": "check_functions",
    }
    target: dict = {}
    for sub, param in sub_to_param.items():
        sub_table = stutter.get(sub)
        if isinstance(sub_table, dict) and _is_leaf_legacy_table(sub_table):
            target[param] = bool(sub_table.get("enabled", True))
            for shared_key in ("min_overlap_tokens", "severity"):
                if shared_key in sub_table:
                    target.setdefault(shared_key, sub_table[shared_key])
            deprecations.append(
                f"  [rules.lexical.stutter.{sub}] -> [rules.lexical.stutter] "
                f"(check_{sub.rstrip('s') + 's'} parameter)"
            )
    if target:
        derived["lexical.stutter"] = target
    return derived, deprecations


def migrate_legacy_rule_tables(
    raw_rules: dict, canonical_keys: set[str],
) -> tuple[dict, list[str]]:
    """Translate legacy ``[rules.<table>]`` keys to the canonical taxonomy.

    ``canonical_keys`` is the set of accepted flat dotted category names
    (i.e. ``DEFAULT_RULE_CONFIGS.keys()``). It is passed in rather than
    imported to avoid a module-level cycle with ``slop.config``.

    Returns ``(new_raw_rules, deprecations)``. ``new_raw_rules`` is a
    flat ``"<canonical category>" -> table`` mapping suitable for
    direct lookup against ``DEFAULT_RULE_CONFIGS``. Canonical entries in
    the input win over values derived from legacy tables.
    """
    derived, deprecations = _collect_legacy_derivations(raw_rules)
    stutter_derived, stutter_deprecations = _migrate_v110_stutter_subrules(raw_rules)
    derived.update(stutter_derived)
    deprecations.extend(stutter_deprecations)
    canonical = _flatten_canonical_tables(raw_rules, canonical_keys)

    merged: dict = dict(derived)
    for key, value in canonical.items():
        if key in merged:
            combined = dict(merged[key])
            combined.update(value)
            merged[key] = combined
        else:
            merged[key] = value
    return merged, deprecations


def format_deprecation_block(lines: list[str]) -> str:
    """Render the consolidated deprecation block printed to stderr."""
    header = (
        f"slop: deprecated rule names detected in config "
        f"(deprecated in {DEPRECATED_IN}, removal in {REMOVED_IN})"
    )
    body = "\n".join(lines)
    footer = "Config still works for now. See docs/CONFIG.md for canonical names."
    return f"{header}\n{body}\n{footer}"
