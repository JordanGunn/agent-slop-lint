"""Orphans rule — wraps Structure.orphans (view-native).

Rule:
  orphans  — symbols with zero detected external references
                        (advisory by default; off by default since static
                        analysis can't see dynamic dispatch).

The advisory framing matters: every candidate needs human verification
before any action, because ripgrep cannot see plugin registration,
reflection, runtime patching, or cross-language calls. Confidence
ratings encode name-length and language risk, not certainty.
"""

from __future__ import annotations

from pathlib import Path

from slop.linter.rule import Rule
from slop.config import Config
from slop.linter.slop import Slop
from slop.linter.tags import Tag
from slop.linter.types import RuleDefinition, RuleResult
from slop.structure.view import Structure

_CONFIDENCE_ORDER = {"high": 3, "medium": 2, "low": 1}


_RULE = Tag.ORPHANS.key

def run(
    structure: Structure,
    rule_config: Rule,
    slop_config: Config,
) -> RuleResult:
    """Report unreferenced symbols at or above a confidence threshold."""
    min_confidence = rule_config.params.get("min_confidence", "high")
    min_confidence_level = _CONFIDENCE_ORDER.get(min_confidence, 3)
    severity = rule_config.severity
    root = Path(slop_config.root).expanduser().resolve()

    result = structure.orphans(root)

    violations: list[Slop] = []
    for candidate in result.candidates:
        if _CONFIDENCE_ORDER.get(candidate.confidence, 0) < min_confidence_level:
            continue
        violations.append(Slop(
            rule="orphans",
            file=candidate.file,
            line=candidate.line if candidate.line > 0 else None,
            symbol=candidate.symbol,
            message=(
                f"{candidate.external_refs} references "
                f"({candidate.confidence} confidence)"
            ),
            severity=severity,
            value=candidate.external_refs,
            threshold=0,
            metadata={
                "symbol_type": candidate.symbol_type,
                "confidence": candidate.confidence,
                "caveats": list(candidate.caveats),
            },
        ))

    return RuleResult(
        rule="orphans",
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "symbols_analyzed": result.symbols_analyzed,
            "candidates_found": len(violations),
            "violation_count": len(violations),
        },
        errors=list(result.errors),
    )

RULE = RuleDefinition(
    name=_RULE,
    category=_RULE,
    description="Unreferenced symbols (advisory)",
    default_severity="warning",
    default_enabled=False,
    threshold_label="",
    run=run,
)
