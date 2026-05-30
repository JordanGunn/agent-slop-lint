"""lexical.sprawl — closed-alphabet sprawl across naming templates.

Flags identifier patterns where a closed alphabet of values recurs
across function-name positions (the language-alphabet case:
``_python_extract``, ``_java_extract``, ``_csharp_extract``). The
alphabet is encoding a type the codebase hasn't declared.

Algorithm lives in ``slop.lexicon.affix``: token-Levenshtein-1
affix patterns (Caprile & Tonella 2000), alphabet clustering, and
Formal Concept Analysis (Wille 1982; Ganter & Wille 1999) over the
inheritance lattice. Detection runs at file → package → root,
claiming alphabet members at the narrowest scope where the pattern
coheres.

See ``docs/methods/lexical/closed_alphabet_entity.md`` and
``docs/methods/lexical/within_cluster_affix.md`` for the
algorithm grounding.
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterable

from slop.linter.rule import Rule
from slop.config import Config
from slop.lexicon.affix import Lexeme, sprawl_over
from slop.linter.slop import Action, Slop
from slop.linter.types import RuleResult
from slop.tree.records import CallableKind
from slop.linter.tags import Tag
from slop.linter.types import RuleDefinition

if TYPE_CHECKING:
    from slop.lexicon.view import Lexicon


from slop.linter.rules.roots import derive_root as _derive_root


_RULE = Tag.SPRAWL.key

def _collect_function_lexemes(
    lexicon: Lexicon, root: Path,
) -> list[Lexeme]:
    """Build the Lexeme list sprawl_over consumes.

    File paths are made relative to ``root`` because the recursive
    namespace traversal partitions by path parts. Lambdas and short
    (< 2 char) names are filtered out — they're noise in alphabet
    extraction.
    """
    items: list[Lexeme] = []
    for c in lexicon.callables():
        if c.kind == CallableKind.LAMBDA:
            continue
        name = c.qualname.rsplit(".", 1)[-1]
        if not name or name.startswith("<") or len(name) < 2:
            continue
        try:
            file_rel = str(c.path.relative_to(root))
        except ValueError:
            file_rel = str(c.path)
        items.append(Lexeme.of(name, file=file_rel, line=c.line))
    return items


def _dispatch_family_names(lexicon: Lexicon, root: Path, exempt_names: frozenset[str]) -> frozenset[str]:
    """Names of functions belonging to an imposters dispatch_family cluster."""
    clusters = lexicon.first_param_clusters(
        min_cluster=3, exempt_names=exempt_names, root=root,
    )
    names: set[str] = set()
    for c in clusters:
        if c.profile_label == "dispatch_family":
            for name, _file, _line in c.members:
                names.add(name)
    return frozenset(names)


# ---- finding-construction helpers --------------------------------------
#
# ``run`` used to inline anchor-finding, member-collection and the
# dispatch branching twice (once per finding kind), which exploded its
# NPath into the hundred-thousands. These pull the nested searches and
# the per-kind Slop construction out, leaving ``run`` two flat loops.


def _anchor_for(clusters: Iterable[Any], keys: Iterable[str]) -> tuple[str, int]:
    """First ``(file, line)`` anchor for any of ``keys`` across patterns.

    Returns ``("", 0)`` when no key has a located member — callers fall
    back to the ``<aggregate>`` sentinel.
    """
    key_list = list(keys)
    for cluster in clusters:
        for pattern in cluster.patterns:
            for key in key_list:
                members = pattern.variants.get(key)
                if members:
                    _, anchor_file, anchor_line = members[0]
                    return anchor_file, anchor_line
    return "", 0


def _child_members(clusters: Iterable[Any], child: str) -> set[str]:
    """All variant member names recorded for ``child`` across patterns."""
    out: set[str] = set()
    for cluster in clusters:
        for pattern in cluster.patterns:
            members = pattern.variants.get(child)
            if members:
                for name, _, _ in members:
                    out.add(name)
    return out


def _extent_in_dispatch(
    clusters: Iterable[Any], extent: Iterable[str], dispatch_names: frozenset[str],
) -> bool:
    """Whether any extent entity's members belong to a dispatch family."""
    extent_set = set(extent)
    for cluster in clusters:
        for pattern in cluster.patterns:
            for entity in extent_set:
                members = pattern.variants.get(entity)
                if members and any(name in dispatch_names for name, _, _ in members):
                    return True
    return False


def _inheritance_finding(
    parent: str, child: str, clusters: Iterable[Any],
    dispatch_names: frozenset[str], severity: str,
) -> Slop:
    """Build the Slop for one inheritance pair (dispatch-aware)."""
    clusters = list(clusters)
    anchor_file, anchor_line = _anchor_for(clusters, (child,))
    in_dispatch = bool(_child_members(clusters, child) & dispatch_names)

    if in_dispatch:
        advice = (
            f"The shared operations reflect a dispatch/plugin "
            f"pattern — the naming overlap is structural, not a "
            f"missing type hierarchy. Consider extracting shared "
            f"logic into a helper rather than introducing a class."
        )
        action = Action.REVIEW_INTENT
        prescription = (
            f"`{child}` and `{parent}` are functions in a dispatch "
            f"family — the naming overlap is structural. Extract "
            f"shared logic into a helper if the bodies converge."
        )
        confidence = 0.5
    else:
        advice = (
            f"Candidate refactor: introduce class "
            f"`{parent.capitalize()}` and `class "
            f"{child.capitalize()}({parent.capitalize()})` to make "
            f"the inheritance explicit."
        )
        action = Action.EXTRACT_CLASS
        prescription = (
            f"Introduce a class hierarchy: `class "
            f"{parent.capitalize()}` and `class "
            f"{child.capitalize()}({parent.capitalize()})`. "
            f"The naming template already shows the inheritance."
        )
        confidence = 0.65

    return Slop(
        rule="lexical.sprawl",
        file=anchor_file or "<aggregate>",
        line=anchor_line or None,
        symbol=child,
        message=(
            f"`{child}` inherits from `{parent}` (every operation "
            f"`{parent}` overrides is also overridden by `{child}`, "
            f"plus more). {advice}"
        ),
        severity=severity,
        action=action,
        prescription=prescription,
        confidence=confidence,
        metadata={
            "kind": "inheritance_pair",
            "parent": parent,
            "child": child,
            "in_dispatch_family": in_dispatch,
        },
    )


def _concept_finding(
    concept: Any, clusters: Iterable[Any],
    dispatch_names: frozenset[str], severity: str,
) -> Slop:
    """Build the Slop for one FCA concept (dispatch-aware)."""
    clusters = list(clusters)
    anchor_file, anchor_line = _anchor_for(clusters, concept.extent)
    entity_list = ", ".join(f"`{e}`" for e in sorted(concept.extent))
    op_list = ", ".join(f"`{o}`" for o in sorted(concept.intent))
    extent_in_dispatch = _extent_in_dispatch(
        clusters, concept.extent, dispatch_names,
    )

    if extent_in_dispatch:
        advice = (
            "These functions belong to a dispatch/plugin family — "
            "the shared operations reflect a registry pattern, not a "
            "missing type. Verify the dispatch is intentional."
        )
        action = Action.REVIEW_INTENT
        prescription = (
            f"Verify the dispatch registry. {len(concept.extent)} "
            f"entities share {len(concept.intent)} operations; this "
            f"is a plugin/dispatch pattern, not a missing type."
        )
        confidence = 0.5
    else:
        advice = (
            "The alphabet is acting as an undeclared type; "
            "consider modeling its members as a class."
        )
        action = Action.EXTRACT_CLASS
        prescription = (
            f"Model the alphabet as a class: {len(concept.extent)} "
            f"entities ({entity_list}) share {len(concept.intent)} "
            f"operations ({op_list}). The recurring template is "
            f"acting as an undeclared type."
        )
        confidence = 0.65

    return Slop(
        rule="lexical.sprawl",
        file=anchor_file or "<aggregate>",
        line=anchor_line or None,
        symbol=f"concept[{len(concept.extent)}×{len(concept.intent)}]",
        message=(
            f"Sprawl: {len(concept.extent)} entities "
            f"({entity_list}) share {len(concept.intent)} operations "
            f"({op_list}). {advice}"
        ),
        severity=severity,
        action=action,
        prescription=prescription,
        confidence=confidence,
        metadata={
            "kind": "concept",
            "extent": sorted(concept.extent),
            "intent": sorted(concept.intent),
            "scope": concept.scope,
            "scope_kind": concept.scope_kind,
            "in_dispatch_family": extent_in_dispatch,
        },
    )


def run(
    lexicon: Lexicon, rule_config: Rule, slop_config: Config,
) -> RuleResult:
    """Detect closed-alphabet sprawl in identifier templates."""
    min_alphabet: int = int(rule_config.params.get("min_alphabet", 3))
    min_concept_extent: int = int(rule_config.params.get("min_concept_extent", 2))
    min_concept_intent: int = int(rule_config.params.get("min_concept_intent", 2))
    severity = rule_config.severity
    root = _derive_root(lexicon, slop_config)

    items = _collect_function_lexemes(lexicon, root)
    result = sprawl_over(items, min_alphabet=min_alphabet)
    dispatch_names = _dispatch_family_names(
        lexicon, root, frozenset(rule_config.params.get("exempt_names", ["self", "cls"])),
    )

    violations: list[Slop] = []

    for parent, child in result.inheritance_pairs:
        violations.append(_inheritance_finding(
            parent, child, result.clusters, dispatch_names, severity,
        ))

    for concept in result.concepts:
        if (len(concept.extent) < min_concept_extent
                or len(concept.intent) < min_concept_intent):
            continue
        violations.append(_concept_finding(
            concept, result.clusters, dispatch_names, severity,
        ))

    return RuleResult(
        rule="lexical.sprawl",
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "functions_checked": result.functions_analyzed,
            "files_searched": result.files_searched,
            "clusters_detected": len(result.clusters),
            "concepts_detected": len(result.concepts),
            "inheritance_pairs": len(result.inheritance_pairs),
            "violation_count": len(violations),
        },
        errors=[],
    )

RULE = RuleDefinition(
    name=_RULE,
    category=_RULE,
    description='Closed alphabet sprawls across naming templates (Wille 1982 FCA)',
    default_severity='warning',
    default_enabled=True,
    threshold_label='≥ 3 alphabet × ≥ 2 ops',
    run=run,
    view="lexicon",
)
