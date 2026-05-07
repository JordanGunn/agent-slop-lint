"""Composition rule wrappers — missing-namespace and missing-receiver detection.

Two rules under the new ``composition.*`` suite:

- ``composition.affix_polymorphism`` — flags clusters of identifiers
  sharing a stem with one position varying over a closed alphabet.
  Surfaces missing namespace / class candidates with their inheritance
  lattice (Formal Concept Analysis).
- ``composition.first_parameter_drift`` — flags groups of functions
  sharing a first parameter, indicating methods on a missing class.

Both are advisory rules (default severity = "warning"). Their job is
to **surface** candidates, not to coerce a specific refactor; whether
a candidate is acted on is a downstream architectural decision.

See ``docs/philosophy/composition-and-lexical.md`` for the empirical
grounding (Wille 1982; Caprile & Tonella 2000; Bavota et al.).
"""
from __future__ import annotations

from pathlib import Path

from slop._structural.composition import (
    affix_polymorphism_kernel,
    first_parameter_drift_kernel,
)
from slop.models import RuleConfig, RuleResult, SlopConfig, Violation


def run_affix_polymorphism(
    root: Path, rule_config: RuleConfig, slop_config: SlopConfig,
) -> RuleResult:
    """Flag missing-namespace candidates from affix-polymorphism + FCA."""
    min_alphabet: int = int(rule_config.params.get("min_alphabet", 3))
    min_concept_extent: int = int(rule_config.params.get("min_concept_extent", 2))
    min_concept_intent: int = int(rule_config.params.get("min_concept_intent", 2))
    severity = rule_config.severity

    result = affix_polymorphism_kernel(
        root,
        languages=slop_config.languages or None,
        excludes=slop_config.exclude or None,
        min_alphabet=min_alphabet,
    )

    violations: list[Violation] = []

    # One violation per inheritance pair — these are the most actionable.
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
            rule="composition.affix_polymorphism",
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

    # One violation per non-trivial concept (≥ extent × ≥ intent).
    for concept in result.concepts:
        if (len(concept.extent) < min_concept_extent
                or len(concept.intent) < min_concept_intent):
            continue
        # Find anchor location: the first member of any pattern matching
        # any entity in extent.
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
            rule="composition.affix_polymorphism",
            file=anchor_file or "<aggregate>",
            line=anchor_line or None,
            symbol=f"concept[{len(concept.extent)}×{len(concept.intent)}]",
            message=(
                f"Missing namespace: {len(concept.extent)} entities "
                f"({entity_list}) share {len(concept.intent)} operations "
                f"({op_list}). Candidate class with these methods; "
                f"each entity becomes an instance or subclass."
            ),
            severity=severity,
            metadata={
                "kind": "concept",
                "extent": sorted(concept.extent),
                "intent": sorted(concept.intent),
            },
        ))

    status = "fail" if violations else "pass"
    return RuleResult(
        rule="composition.affix_polymorphism",
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


def run_first_parameter_drift(
    root: Path, rule_config: RuleConfig, slop_config: SlopConfig,
) -> RuleResult:
    """Flag missing-receiver candidates from first-parameter clustering."""
    min_cluster: int = int(rule_config.params.get("min_cluster", 3))
    raw_exempt = rule_config.params.get("exempt_names",
                                        ["self", "cls"])
    exempt_names = frozenset(raw_exempt) if raw_exempt else frozenset()
    severity = rule_config.severity

    result = first_parameter_drift_kernel(
        root,
        languages=slop_config.languages or None,
        excludes=slop_config.exclude or None,
        min_cluster=min_cluster,
        exempt_names=exempt_names,
    )

    violations: list[Violation] = []
    for cluster in result.clusters:
        # Only emit violations for strong candidates by default; weak
        # and false-positive entries inform via the summary but don't
        # become violations.
        if cluster.verdict != "strong":
            continue
        anchor_name, anchor_file, anchor_line = cluster.members[0]
        scope_phrase = (
            f"in `{cluster.scope}`" if cluster.scope_kind == "file"
            else f"under `{cluster.scope}/`" if cluster.scope_kind == "package"
            else "across the codebase"
        )
        violations.append(Violation(
            rule="composition.first_parameter_drift",
            file=anchor_file,
            line=anchor_line,
            symbol=cluster.parameter_name,
            message=(
                f"{len(cluster.members)} functions {scope_phrase} share "
                f"`{cluster.parameter_name}` as first parameter. "
                f"{cluster.advisory}"
            ),
            severity=severity,
            metadata={
                "verdict": cluster.verdict,
                "scope": cluster.scope,
                "scope_kind": cluster.scope_kind,
                "members": [
                    {"name": n, "file": f, "line": l}
                    for n, f, l in cluster.members
                ],
                "parameter_types": sorted(cluster.parameter_types),
            },
        ))

    status = "fail" if violations else "pass"
    return RuleResult(
        rule="composition.first_parameter_drift",
        status=status,
        violations=violations,
        summary={
            "functions_checked": result.functions_analyzed,
            "files_searched": result.files_searched,
            "clusters_detected": len(result.clusters),
            "strong_clusters": sum(1 for c in result.clusters if c.verdict == "strong"),
            "weak_clusters": sum(1 for c in result.clusters if c.verdict == "weak"),
            "false_positive_clusters": sum(1 for c in result.clusters if c.verdict == "false_positive"),
            "violation_count": len(violations),
        },
        errors=list(result.errors),
    )
