"""lexical.sprawl — closed-alphabet sprawl across naming templates.

Flags identifier patterns where a closed alphabet of values
recurs across function-name positions (the language alphabet
case: ``_python_extract``, ``_java_extract``, ``_csharp_extract``).
The alphabet is encoding a type the codebase hasn't declared.

The kernel uses recursive namespace scoping: clusters are
reported at the narrowest scope where they cohere
(file → package → root). Each finding's metadata identifies the
scope.

See ``docs/methods/lexical/closed_alphabet_entity.md`` and
``docs/methods/lexical/within_cluster_affix.md`` for the
algorithm grounding (Wille 1982; Caprile & Tonella 2000).
"""
from __future__ import annotations

from pathlib import Path

from slop._lexical.sprawl import sprawl_kernel
from slop.models import RuleConfig, RuleResult, SlopConfig, Violation


def run_sprawl(
    root: Path, rule_config: RuleConfig, slop_config: SlopConfig,
) -> RuleResult:
    """Flag closed-alphabet sprawl in identifier templates."""
    min_alphabet: int = int(rule_config.params.get("min_alphabet", 3))
    min_concept_extent: int = int(rule_config.params.get("min_concept_extent", 2))
    min_concept_intent: int = int(rule_config.params.get("min_concept_intent", 2))
    severity = rule_config.severity

    result = sprawl_kernel(
        root,
        languages=slop_config.languages or None,
        excludes=slop_config.exclude or None,
        min_alphabet=min_alphabet,
    )

    violations: list[Violation] = []

    # One violation per inheritance pair — most actionable.
    for parent, child in result.inheritance_pairs:
        anchor_file: str = ""
        anchor_line: int = 0
        for cluster in result.clusters:
            for pattern in cluster.patterns:
                if child in pattern.variants:
                    members = pattern.variants[child]
                    if members:
                        _, anchor_file, anchor_line = members[0]
                        break
            if anchor_file:
                break
        violations.append(Violation(
            rule="lexical.sprawl",
            file=anchor_file or "<aggregate>",
            line=anchor_line or None,
            symbol=child,
            message=(
                f"`{child}` inherits from `{parent}` (every operation "
                f"`{parent}` overrides is also overridden by `{child}`, "
                f"plus more). Candidate refactor: introduce class "
                f"`{parent.capitalize()}` and `class "
                f"{child.capitalize()}({parent.capitalize()})` to make "
                f"the inheritance explicit."
            ),
            severity=severity,
            metadata={
                "kind": "inheritance_pair",
                "parent": parent,
                "child": child,
            },
        ))

    # One violation per non-trivial concept.
    for concept in result.concepts:
        if (len(concept.extent) < min_concept_extent
                or len(concept.intent) < min_concept_intent):
            continue
        anchor_file = ""
        anchor_line = 0
        for cluster in result.clusters:
            for pattern in cluster.patterns:
                for entity in concept.extent:
                    if entity in pattern.variants and pattern.variants[entity]:
                        _, anchor_file, anchor_line = pattern.variants[entity][0]
                        break
                if anchor_file:
                    break
            if anchor_file:
                break
        entity_list = ", ".join(f"`{e}`" for e in sorted(concept.extent))
        op_list = ", ".join(f"`{o}`" for o in sorted(concept.intent))
        violations.append(Violation(
            rule="lexical.sprawl",
            file=anchor_file or "<aggregate>",
            line=anchor_line or None,
            symbol=f"concept[{len(concept.extent)}×{len(concept.intent)}]",
            message=(
                f"Sprawl: {len(concept.extent)} entities "
                f"({entity_list}) share {len(concept.intent)} operations "
                f"({op_list}). The alphabet is acting as an undeclared "
                f"type; consider modeling its members as a class."
            ),
            severity=severity,
            metadata={
                "kind": "concept",
                "extent": sorted(concept.extent),
                "intent": sorted(concept.intent),
                "scope": concept.scope,
                "scope_kind": concept.scope_kind,
            },
        ))

    status = "fail" if violations else "pass"
    return RuleResult(
        rule="lexical.sprawl",
        status=status,
        violations=violations,
        summary={
            "functions_checked": result.functions_analyzed,
            "files_searched": result.files_searched,
            "clusters_detected": len(result.clusters),
            "concepts_detected": len(result.concepts),
            "inheritance_pairs": len(result.inheritance_pairs),
            "violation_count": len(violations),
        },
        errors=list(result.errors),
    )
