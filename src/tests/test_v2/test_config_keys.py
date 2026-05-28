"""Tests for ``slop.linter.tags`` — Tag enum + Key composition.

Two guarantees:

1. Each ``Tag`` enum member resolves to the expected segment string,
   and each grouping classmethod returns the expected frozenset.
2. Each ``Key`` leaf composes to the expected bare-name dotted key.

Rule names are bare under the scope-as-first-class design (no
``function./class./module./parameter./package.`` prefix). Scope lives
on ``RuleDefinition.scopes`` and ``Slop.scope`` instead of in the name.
"""
from __future__ import annotations

from slop.linter.tags import Tag


# ---------------------------------------------------------------------------
# Flat Tag enum — path-segment atoms
# ---------------------------------------------------------------------------


class TestTagScopeMembers:
    """The scope-name members of the Tag enum."""

    def test_function(self):
        assert Tag.FUNCTION == "function"

    def test_class(self):
        assert Tag.CLASS == "class"

    def test_module(self):
        assert Tag.MODULE == "module"

    def test_parameter(self):
        assert Tag.PARAMETER == "parameter"

    def test_package(self):
        assert Tag.PACKAGE == "package"


class TestTagNamespaceRoots:
    def test_complexity(self):
        assert Tag.COMPLEXITY == "complexity"

    def test_inheritance(self):
        assert Tag.INHERITANCE == "inheritance"

    def test_lexical(self):
        assert Tag.LEXICAL == "lexical"


class TestTagStandaloneLeaves:
    def test_coupling(self):
        assert Tag.COUPLING == "coupling"

    def test_magic_literals(self):
        assert Tag.MAGIC_LITERALS == "magic_literals"

    def test_god_module(self):
        assert Tag.GOD_MODULE == "god_module"

    def test_escape_hatches(self):
        assert Tag.ESCAPE_HATCHES == "escape_hatches"

    def test_hidden_mutators(self):
        assert Tag.HIDDEN_MUTATORS == "hidden_mutators"

    def test_sentinels(self):
        assert Tag.SENTINELS == "sentinels"

    def test_rigidity(self):
        assert Tag.RIGIDITY == "rigidity"

    def test_uselessness(self):
        assert Tag.USELESSNESS == "uselessness"

    def test_cross_cutting(self):
        assert Tag.HOTSPOTS == "hotspots"
        assert Tag.DEPS == "deps"
        assert Tag.ORPHANS == "orphans"
        assert Tag.REDUNDANCY == "redundancy"
        assert Tag.DUPLICATION == "duplication"


class TestTagMetricLeaves:
    def test_complexity_leaves(self):
        assert Tag.CYCLOMATIC == "cyclomatic"
        assert Tag.COGNITIVE == "cognitive"
        assert Tag.COMBINATORIAL == "combinatorial"
        assert Tag.VOLUME == "volume"
        assert Tag.DENSITY == "density"

    def test_inheritance_leaves(self):
        assert Tag.DEPTH == "depth"
        assert Tag.CHILDREN == "children"

    def test_lexical_leaves(self):
        assert Tag.STUTTER == "stutter"
        assert Tag.VERBOSITY == "verbosity"
        assert Tag.HAMMERS == "hammers"
        assert Tag.SPRAWL == "sprawl"
        assert Tag.IMPOSTERS == "imposters"
        assert Tag.SLACKERS == "slackers"
        assert Tag.CONFUSION == "confusion"


# ---------------------------------------------------------------------------
# Tag grouping classmethods
# ---------------------------------------------------------------------------


class TestTagGroupings:
    def test_complexity_group(self):
        assert Tag.complexity() == frozenset({
            Tag.CYCLOMATIC, Tag.COGNITIVE, Tag.COMBINATORIAL,
            Tag.VOLUME, Tag.DENSITY,
        })

    def test_inheritance_group(self):
        assert Tag.inheritance() == frozenset({Tag.DEPTH, Tag.CHILDREN})

    def test_lexical_group(self):
        assert Tag.lexical() == frozenset({
            Tag.STUTTER, Tag.VERBOSITY, Tag.HAMMERS,
            Tag.SPRAWL, Tag.IMPOSTERS, Tag.SLACKERS,
            Tag.CONFUSION,
        })

    def test_namespaces_group(self):
        assert Tag.namespaces() == frozenset({
            Tag.COMPLEXITY, Tag.INHERITANCE, Tag.LEXICAL,
        })

    def test_scopes_group(self):
        assert Tag.scopes() == frozenset({
            Tag.FUNCTION, Tag.CLASS, Tag.MODULE, Tag.PACKAGE, Tag.PARAMETER,
        })


# ---------------------------------------------------------------------------
# Composed Key leaves — these are the canonical bare names
# ---------------------------------------------------------------------------


class TestStandaloneLeaves:
    def test_coupling(self):
        assert Tag.COUPLING == "coupling"

    def test_magic_literals(self):
        assert Tag.MAGIC_LITERALS == "magic_literals"

    def test_god_module(self):
        assert Tag.GOD_MODULE == "god_module"

    def test_escape_hatches(self):
        assert Tag.ESCAPE_HATCHES == "escape_hatches"

    def test_hidden_mutators(self):
        assert Tag.HIDDEN_MUTATORS == "hidden_mutators"

    def test_sentinels(self):
        assert Tag.SENTINELS == "sentinels"

    def test_rigidity(self):
        assert Tag.RIGIDITY == "rigidity"

    def test_uselessness(self):
        assert Tag.USELESSNESS == "uselessness"

    def test_hotspots(self):
        assert Tag.HOTSPOTS == "hotspots"

    def test_deps(self):
        assert Tag.DEPS == "deps"

    def test_orphans(self):
        assert Tag.ORPHANS == "orphans"

    def test_redundancy(self):
        assert Tag.REDUNDANCY == "redundancy"

    def test_duplication(self):
        assert Tag.DUPLICATION == "duplication"


class TestComplexityLeaves:
    def test_cyclomatic(self):
        assert Tag.CYCLOMATIC.key == "complexity.cyclomatic"

    def test_cognitive(self):
        assert Tag.COGNITIVE.key == "complexity.cognitive"

    def test_combinatorial(self):
        assert Tag.COMBINATORIAL.key == "complexity.combinatorial"

    def test_volume(self):
        assert Tag.VOLUME.key == "complexity.volume"

    def test_density(self):
        assert Tag.DENSITY.key == "complexity.density"


class TestInheritanceLeaves:
    def test_depth(self):
        assert Tag.DEPTH.key == "inheritance.depth"

    def test_children(self):
        assert Tag.CHILDREN.key == "inheritance.children"


class TestLexicalLeaves:
    def test_stutter(self):
        assert Tag.STUTTER.key == "lexical.stutter"

    def test_verbosity(self):
        assert Tag.VERBOSITY.key == "lexical.verbosity"

    def test_hammers(self):
        assert Tag.HAMMERS.key == "lexical.hammers"

    def test_sprawl(self):
        assert Tag.SPRAWL.key == "lexical.sprawl"

    def test_imposters(self):
        assert Tag.IMPOSTERS.key == "lexical.imposters"

    def test_slackers(self):
        assert Tag.SLACKERS.key == "lexical.slackers"

    def test_confusion(self):
        assert Tag.CONFUSION.key == "lexical.confusion"


# ---------------------------------------------------------------------------
# Registry scope coverage
# ---------------------------------------------------------------------------


class TestRuleDefinitionScopes:
    """RuleDefinition.scopes is the first-class scope declaration."""

    def test_multi_scope_complexity_rules(self):
        from slop.linter import RULE_REGISTRY
        by_name = {r.name: r for r in RULE_REGISTRY}
        assert by_name[Tag.CYCLOMATIC.key].scopes == ("function", "class")
        assert by_name[Tag.COGNITIVE.key].scopes == ("function", "class")
        assert by_name[Tag.COMBINATORIAL.key].scopes == ("function", "class")
        assert by_name[Tag.VOLUME.key].scopes == ("function", "class")

    def test_density_is_function_scope_only(self):
        from slop.linter import RULE_REGISTRY
        by_name = {r.name: r for r in RULE_REGISTRY}
        assert by_name[Tag.DENSITY.key].scopes == ("function",)

    def test_class_only_rules(self):
        from slop.linter import RULE_REGISTRY
        by_name = {r.name: r for r in RULE_REGISTRY}
        assert by_name[Tag.COUPLING].scopes == ("class",)
        assert by_name[Tag.DEPTH.key].scopes == ("class",)
        assert by_name[Tag.CHILDREN.key].scopes == ("class",)

    def test_package_only_rules(self):
        from slop.linter import RULE_REGISTRY
        by_name = {r.name: r for r in RULE_REGISTRY}
        assert by_name[Tag.RIGIDITY].scopes == ("package",)
        assert by_name[Tag.USELESSNESS].scopes == ("package",)

    def test_cross_cutting_rules_have_empty_scopes(self):
        from slop.linter import RULE_REGISTRY
        by_name = {r.name: r for r in RULE_REGISTRY}
        assert by_name[Tag.HOTSPOTS].scopes == ()
        assert by_name[Tag.DEPS].scopes == ()
        assert by_name[Tag.ORPHANS].scopes == ()
        assert by_name[Tag.REDUNDANCY].scopes == ()
        assert by_name[Tag.DUPLICATION].scopes == ()
