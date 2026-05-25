"""Escape-hatch type density — fraction of type annotations using the universal escape type.

Rules:
  ``types.escape_hatches``  — flag files where a significant
    fraction of type annotations use the language's escape-hatch type
    (Python ``Any``, TS ``any``, Go ``any``/``interface{}``, Java
    ``Object``, C# ``object``/``dynamic``, Rust ``dyn Any``, Julia
    ``Any``).

Config params
-------------
  threshold       float  Maximum tolerated density (0.0–1.0). Default
                         0.30 (flag if >30% of annotations are escape
                         hatches).
  min_annotations int    Minimum annotation count before density is
                         computed. Avoids noise from files with only
                         1–2 annotations. Default 5.
"""
from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from slop.linter.tags import Tag
from slop.linter.rule_config import RuleConfig
from slop.config import Config
from slop.linter.slop import Slop
from slop.linter.types import RuleResult
from slop.linter.types import RuleDefinition

if TYPE_CHECKING:
    from slop.structure.view import Structure

DEFAULT_THRESHOLD = 0.30
DEFAULT_MIN_ANNOTATIONS = 5
PRECISION = 4


def run_escape_hatches(
    structure: Structure, rule_config: RuleConfig, slop_config: Config,
) -> RuleResult:
    """Flag files where too many type annotations use escape-hatch types."""
    del slop_config
    thresholds = rule_config.params.get("thresholds", {}) or {}
    if "module" not in thresholds:
        return RuleResult(
            rule=Tag.ESCAPE_HATCHES.key, status="pass", violations=[],
            summary={"files_scanned": 0, "violations": 0},
        )
    threshold = float(thresholds.get("module", DEFAULT_THRESHOLD))
    min_annotations = int(
        rule_config.params.get("min_annotations", DEFAULT_MIN_ANNOTATIONS),
    )
    severity = rule_config.severity

    per_file: dict[str, dict[str, int]] = defaultdict(
        lambda: {"escape": 0, "total": 0},
    )
    language_by_file: dict[str, str] = {}
    for ann in structure.type_annotations():
        per_file[ann.file]["total"] += 1
        if ann.is_escape:
            per_file[ann.file]["escape"] += 1
        if ann.file not in language_by_file:
            language_by_file[ann.file] = (
                structure._language_by_path.get(ann.file) or "unknown"
            )

    violations: list[Slop] = []
    files_scanned = 0
    for file, counts in per_file.items():
        files_scanned += 1
        total = counts["total"]
        escape = counts["escape"]
        if total < min_annotations:
            continue
        density = escape / total if total else 0.0
        if density <= threshold:
            continue
        pct = density * 100
        violations.append(Slop(
            rule=Tag.ESCAPE_HATCHES.key,
            file=file,
            line=None,
            symbol=None,
            message=(
                f"{pct:.1f}% of type annotations use escape-hatch types "
                f"({escape}/{total})"
            ),
            severity=severity,
            value=round(density, PRECISION),
            threshold=threshold,
            metadata={
                "language": language_by_file.get(file, "unknown"),
                "escape_count": escape,
                "total_count": total,
                "density": density,
            },
            scope="module",
        ))

    return RuleResult(
        rule=Tag.ESCAPE_HATCHES.key,
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "files_scanned": files_scanned,
            "violations": len(violations),
            "threshold": threshold,
        },
    )

RULE = RuleDefinition(
    name=Tag.ESCAPE_HATCHES.key,
    category=Tag.ESCAPE_HATCHES.key,
    description='Fraction of type annotations using escape-hatch types (Any, interface{}, ...)',
    default_severity='warning',
    default_enabled=True,
    threshold_label='> 30%',
    run=run_escape_hatches,
    scopes=('module',),
)
