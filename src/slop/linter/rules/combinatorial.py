"""Combinatorial complexity — NPath at function and class scope.

  ``complexity.combinatorial`` —
    function: per-function NPath (Nejmeh 1988)
    class:    sum of per-method NPaths (slop calibration; no published threshold)

Per-scope thresholds live in ``rule_config.params['thresholds']``.
"""
from __future__ import annotations

from pathlib import Path

from slop.linter.tags import Tag
from slop.linter.rule import Rule
from slop.config import Config
from slop.linter.slop import Slop
from slop.linter.types import RuleResult
from slop.linter.rules._class_index import _class_index, _slop
from slop.structure.view import Structure
from slop.linter.types import RuleDefinition


_RULE = Tag.COMBINATORIAL.key

def run(
    structure: Structure,
    rule_config: Rule,
    slop_config: Config,
) -> RuleResult:
    """NPath at function scope and class scope."""
    thresholds = rule_config.params.get("thresholds", {}) or {}
    severity = rule_config.severity
    root = Path(slop_config.root).expanduser().resolve()

    findings: list[tuple[int, Slop]] = []
    functions_checked = 0
    classes_checked = 0

    fn_threshold = thresholds.get("function")
    if fn_threshold is not None:
        for c in structure.callables():
            functions_checked += 1
            np = structure.combinatorial(c)
            if np > fn_threshold:
                try:
                    rel = str(c.path.relative_to(root))
                except ValueError:
                    rel = str(c.path)
                findings.append((np, Slop(
                    rule=_RULE,
                    file=rel,
                    line=c.line,
                    symbol=c.qualname.split(".")[-1],
                    message=f"NPath {np} exceeds {fn_threshold}",
                    severity=severity,
                    value=np,
                    threshold=fn_threshold,
                    metadata={"end_line": c.end_line, "qualname": c.qualname},
                    scope="function",
                )))

    cls_threshold = thresholds.get("class")
    if cls_threshold:
        groups, _, _, _ = _class_index(structure)
        for canonical, members in groups:
            classes_checked += 1
            agg = sum(structure.weighted_combinatorial(m) for m in members)
            if agg > cls_threshold:
                slop = _slop(
                    _RULE, canonical, root, severity,
                    agg, cls_threshold,
                    f"Class NPath sum {agg} exceeds {cls_threshold}",
                )
                slop.scope = "class"
                findings.append((agg, slop))

    findings.sort(key=lambda t: -t[0])
    violations = [s for _, s in findings]

    return RuleResult(
        rule=_RULE,
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "functions_checked": functions_checked,
            "classes_checked": classes_checked,
            "violation_count": len(violations),
        },
        errors=[],
    )

RULE = RuleDefinition(
    name=_RULE,
    category=Tag.COMPLEXITY.key,
    description='NPath: Nejmeh 1988 per function; method-sum per class (slop calibration)',
    default_severity='error',
    default_enabled=True,
    threshold_label='NPath > 400 / Σ > 1600',
    run=run,
    scopes=('function', 'class'),
)
