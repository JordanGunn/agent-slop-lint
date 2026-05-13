"""Halstead complexity rules — view-native (v2).

  structural.difficulty.volume    — Halstead V = N · log₂(η)
  structural.difficulty.density   — Halstead D = (η₁/2) · (N₂/η₂)

Halstead's software-science metrics treat each function body as a
stream of tokens classified into operators (keywords, operator
symbols) and operands (identifiers, literals). The metrics then
measure:

    η₁  = distinct operators
    η₂  = distinct operands
    N₁  = total operator tokens
    N₂  = total operand tokens

Derived:

    vocabulary  η  = η₁ + η₂
    length      N  = N₁ + N₂
    volume      V  = N · log₂(η)             [V > 1500 ≈ very large fn]
    density     D  = (η₁ / 2) · (N₂ / η₂)    [reuses-per-operand × ops-half]
    (effort, time-to-program also derivable but not exposed as rules.)

The rules formerly lived under ``information.*`` in v1.x. They moved
to ``structural.difficulty.*`` in v2.0 because the McCabe/Campbell/Nejmeh
control-flow complexity family is methodologically distinct from
Halstead's vocabulary/symbol-density family; bundling them under one
``structural.complexity.*`` namespace would erase that distinction.
The legacy ``difficulty`` leaf was relabeled ``density`` to describe
what the metric actually measures (operand-reuse density), shedding
Halstead's anthropomorphic "difficulty" naming.

Legacy aliases ``information.volume`` / ``information.difficulty`` /
``halstead.volume`` / ``halstead.difficulty`` resolve via
``slop._compat``.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from slop.config.models import RuleConfig, SlopConfig
from slop.language.grammars import LANGUAGE_BY_ID
from slop.linter.slop import Slop
from slop.linter.types import RuleResult
from slop.structure.view import Structure, _resolve_body


def run_volume_v2(
    structure: Structure,
    rule_config: RuleConfig,
    slop_config: SlopConfig,
) -> RuleResult:
    """Flag functions whose Halstead Volume exceeds the threshold."""
    threshold: float = float(rule_config.params.get("threshold", 1500))
    severity = rule_config.severity
    root = Path(slop_config.root).expanduser().resolve()

    findings: list[tuple[float, Slop]] = []
    functions_analyzed = 0

    for c in structure.callables():
        functions_analyzed += 1
        metrics = _halstead_for(structure, c)
        if metrics is None:
            continue
        n1, n2, total_n1, total_n2 = metrics
        if n1 + n2 == 0:
            continue
        volume = (total_n1 + total_n2) * math.log2(n1 + n2)
        if volume > threshold:
            findings.append((volume, _slop(
                "structural.difficulty.volume",
                c, root, severity, volume, threshold,
                f"Volume {volume:.1f} exceeds {threshold:.0f}",
                {"n1": n1, "n2": n2, "total_n1": total_n1, "total_n2": total_n2},
            )))

    findings.sort(key=lambda t: -t[0])
    violations = [s for _, s in findings]

    return RuleResult(
        rule="structural.difficulty.volume",
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "functions_analyzed": functions_analyzed,
            "violations": len(violations),
            "threshold": threshold,
        },
        errors=[],
    )


def run_density_v2(
    structure: Structure,
    rule_config: RuleConfig,
    slop_config: SlopConfig,
) -> RuleResult:
    """Flag functions whose Halstead D (operand-reuse density) exceeds the threshold."""
    threshold: float = float(rule_config.params.get("threshold", 30))
    severity = rule_config.severity
    root = Path(slop_config.root).expanduser().resolve()

    findings: list[tuple[float, Slop]] = []
    functions_analyzed = 0

    for c in structure.callables():
        functions_analyzed += 1
        metrics = _halstead_for(structure, c)
        if metrics is None:
            continue
        n1, n2, _total_n1, total_n2 = metrics
        if n2 == 0:
            continue
        density = (n1 / 2) * (total_n2 / n2)
        if density > threshold:
            findings.append((density, _slop(
                "structural.difficulty.density",
                c, root, severity, density, threshold,
                f"Density {density:.1f} exceeds {threshold:.0f}",
                {"n1": n1, "n2": n2, "total_n2": total_n2},
            )))

    findings.sort(key=lambda t: -t[0])
    violations = [s for _, s in findings]

    return RuleResult(
        rule="structural.difficulty.density",
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "functions_analyzed": functions_analyzed,
            "violations": len(violations),
            "threshold": threshold,
        },
        errors=[],
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _halstead_for(
    structure: Structure, c: Any,
) -> tuple[int, int, int, int] | None:
    """Compute (η₁, η₂, N₁, N₂) for one callable. None if not computable."""
    language_id = structure.language_for(c)
    if language_id is None:
        return None
    lang = LANGUAGE_BY_ID.get(language_id)
    if lang is None:
        return None
    operator_set = lang.operator_nodes()
    operand_set = lang.operand_nodes()
    if not operator_set and not operand_set:
        return None
    node = structure._node_by_key.get((str(c.path), c.qualname))  # noqa: SLF001
    content = structure._content_by_key.get((str(c.path), c.qualname))  # noqa: SLF001
    if node is None or content is None:
        return None
    # Halstead operates over the function BODY, not its name/parameter list.
    # _resolve_body honours C++ template_declaration unwrap before descending
    # to the body field.
    walk_from = _resolve_body(node, lang.definition_unwrap_types())
    nested_callables = lang.callable()
    return _collect_tokens(walk_from, content, operator_set, operand_set, nested_callables)


def _collect_tokens(
    root_node: Any,
    content: bytes,
    operator_set: frozenset[str],
    operand_set: frozenset[str],
    nested_callables: frozenset[str],
) -> tuple[int, int, int, int]:
    """Walk ``root_node``, count unique + total operator/operand leaves.

    Returns (η₁, η₂, N₁, N₂). Skips into nested callables — each
    callable's Halstead metrics are body-local. Only LEAF nodes
    (no children) contribute; intermediate-shape nodes are descended
    through.
    """
    operators: set[str] = set()
    operands: set[str] = set()
    total_n1 = 0
    total_n2 = 0

    stack: list[Any] = [root_node]
    while stack:
        cur = stack.pop()
        ctype = cur.type
        if ctype in nested_callables and cur is not root_node:
            continue
        if cur.child_count == 0:
            if ctype in operator_set:
                text = content[cur.start_byte:cur.end_byte].decode("utf-8", errors="replace")
                operators.add(text)
                total_n1 += 1
            elif ctype in operand_set:
                text = content[cur.start_byte:cur.end_byte].decode("utf-8", errors="replace")
                operands.add(text)
                total_n2 += 1
        for child in reversed(cur.children):
            stack.append(child)

    return len(operators), len(operands), total_n1, total_n2


def _slop(
    rule: str,
    c: Any,
    root: Path,
    severity: str,
    value: float,
    threshold: float,
    message: str,
    extra: dict,
) -> Slop:
    try:
        rel = str(c.path.relative_to(root))
    except ValueError:
        rel = str(c.path)
    metadata: dict[str, Any] = {"end_line": c.end_line, "qualname": c.qualname, **extra}
    return Slop(
        rule=rule,
        file=rel,
        line=c.line,
        symbol=c.qualname.split(".")[-1],
        message=message,
        severity=severity,
        value=value,
        threshold=threshold,
        metadata=metadata,
    )
