"""Rule-key path-segment tags + the canonical scope vocabulary.

Every dotted-key segment slop's rule namespace contains is declared
once as a member of the flat ``Tag`` StrEnum. Canonical rule names
are composed via ``Tag.X.key`` — the ``.key`` property auto-detects
the namespace parent (``complexity.*``, ``inheritance.*``, ``lexical.*``)
via the grouping classmethods on ``Tag``. No string literal for a
path segment lives anywhere outside this file.

The taxonomy is **bare-name**: rule names describe what they measure,
not where they emit. Scope is first-class — declared on each
``RuleDefinition`` as a ``scopes: tuple[str, ...]`` field and surfaced
on each finding via ``Slop.scope``. The same rule emits at multiple
scopes (e.g., ``complexity.cyclomatic`` runs at function and class
scope) with per-scope thresholds in config.

The ``Scope`` enum below is the closed vocabulary of scope identifiers
that ``RuleDefinition.scopes`` and ``Slop.scope`` may take.
"""
from __future__ import annotations

from enum import StrEnum


# ---------------------------------------------------------------------------
# Rule-name path segments
# ---------------------------------------------------------------------------


class Tag(StrEnum):
    """Top-level segments of the rule namespace.

    Sub-namespace roots (complexity, inheritance, lexical) hold related
    families; leaves (coupling, magic_literals, hotspots, etc.) are
    standalone rules.
    """
    FUNCTION = "function"
    CLASS = "class"
    MODULE = "module"
    PARAMETER = "parameter"
    PACKAGE = "package"
    COMPLEXITY = "complexity"
    INHERITANCE = "inheritance"
    LEXICAL = "lexical"
    COUPLING = "coupling"
    MAGIC_LITERALS = "magic_literals"
    GOD_MODULE = "god_module"
    ESCAPE_HATCHES = "escape_hatches"
    HIDDEN_MUTATORS = "hidden_mutators"
    SENTINELS = "sentinels"
    RIGIDITY = "rigidity"
    USELESSNESS = "uselessness"
    HOTSPOTS = "hotspots"
    DEPS = "deps"
    ORPHANS = "orphans"
    REDUNDANCY = "redundancy"
    DUPLICATION = "duplication"
    CYCLOMATIC = "cyclomatic"
    COGNITIVE = "cognitive"
    COMBINATORIAL = "combinatorial"
    VOLUME = "volume"
    DENSITY = "density"
    DEPTH = "depth"
    CHILDREN = "children"
    STUTTER = "stutter"
    VERBOSITY = "verbosity"
    HAMMERS = "hammers"
    SPRAWL = "sprawl"
    IMPOSTERS = "imposters"
    SLACKERS = "slackers"
    CONFUSION = "confusion"

    @property
    def parent(self) -> str:
        """Return the namespace parent tag value for a leaf, or "" for top-level tags.

        Leaves of ``complexity.*`` / ``inheritance.*`` / ``lexical.*``
        return ``"complexity"`` / ``"inheritance"`` / ``"lexical"``.
        Standalone leaves (coupling, hotspots, etc.) and the namespace
        roots themselves return the empty string.
        """
        if self in Tag.complexity():
            return Tag.COMPLEXITY
        if self in Tag.inheritance():
            return Tag.INHERITANCE
        if self in Tag.lexical():
            return Tag.LEXICAL
        return ""

    @property
    def key(self) -> str:
        """Get the full key string for the tag."""
        _parent = self.parent
        if _parent:
            _parent += "."

        return _parent + self.value


    @classmethod
    def complexity(cls) -> frozenset[str]:
        """The five complexity rule tags, for composition into the full rule keys."""
        tags = {
            cls.CYCLOMATIC,
            cls.COGNITIVE,
            cls.COMBINATORIAL,
            cls.VOLUME,
            cls.DENSITY,
        }
        return frozenset(tags)

    @classmethod
    def inheritance(cls) -> frozenset[str]:
        """The two inheritance rule tags, for composition into the full rule keys."""
        tags = {
            cls.DEPTH,
            cls.CHILDREN,
        }

        return frozenset(tags)

    @classmethod
    def namespaces(cls) -> frozenset[str]:
        """The top-level namespaces, for composition into the full rule keys."""
        namespaces = {
            cls.COMPLEXITY,
            cls.INHERITANCE,
            cls.LEXICAL,
        }
        return frozenset(namespaces)

    @classmethod
    def lexical(cls) -> frozenset[str]:
        """The seven lexical rule tags, for composition into the full rule keys."""
        tags = {
            cls.STUTTER,
            cls.VERBOSITY,
            cls.HAMMERS,
            cls.SPRAWL,
            cls.IMPOSTERS,
            cls.SLACKERS,
            cls.CONFUSION,
        }
        return frozenset(tags)

    @classmethod
    def scopes(cls) -> frozenset[str]:
        """The five emission scopes a rule may declare on ``RuleDefinition.scopes``."""
        tags = {
            cls.FUNCTION,
            cls.CLASS,
            cls.MODULE,
            cls.PACKAGE,
            cls.PARAMETER,
        }
        return frozenset(tags)

