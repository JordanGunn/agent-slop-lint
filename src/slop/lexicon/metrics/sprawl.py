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
from typing import TYPE_CHECKING

from slop.linter.rule_config import RuleConfig
from slop.config import Config
from slop.lexicon.affix import Lexeme, sprawl_over
from slop.linter.slop import Slop
from slop.linter.types import RuleResult
from slop.tree.records import CallableKind
from slop.linter.tags import Tag
from slop.linter.types import RuleDefinition

if TYPE_CHECKING:
    from slop.lexicon.view import Lexicon


def _derive_root(lexicon: Lexicon, slop_config: Config) -> Path:
    """Choose the search root.

    Prefer ``slop_config.root`` when explicitly set; otherwise the
    longest common directory across the lexicon's parses.
    """
    if slop_config.root and slop_config.root != ".":
        return Path(slop_config.root).expanduser().resolve()
    import os
    paths = [p.path for p in lexicon._parses]  # noqa: SLF001
    if paths:
        common = Path(os.path.commonpath([str(p) for p in paths]))
        return common.parent if common.is_file() else common
    if slop_config.root:
        return Path(slop_config.root).expanduser().resolve()
    return Path.cwd()


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


def run_sprawl(
    lexicon: Lexicon, rule_config: RuleConfig, slop_config: Config,
) -> RuleResult:
    """Detect closed-alphabet sprawl in identifier templates."""
    min_alphabet: int = int(rule_config.params.get("min_alphabet", 3))
    min_concept_extent: int = int(rule_config.params.get("min_concept_extent", 2))
    min_concept_intent: int = int(rule_config.params.get("min_concept_intent", 2))
    severity = rule_config.severity
    root = _derive_root(lexicon, slop_config)

    items = _collect_function_lexemes(lexicon, root)
    result = sprawl_over(items, min_alphabet=min_alphabet)

    violations: list[Slop] = []

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
        violations.append(Slop(
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
        violations.append(Slop(
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
        errors=[],
    )

RULE = RuleDefinition(
    name=Tag.SPRAWL.key,
    category=Tag.SPRAWL.key,
    description='Closed alphabet sprawls across naming templates (Wille 1982 FCA)',
    default_severity='warning',
    default_enabled=True,
    threshold_label='≥ 3 alphabet × ≥ 2 ops',
    run=run_sprawl,
)
