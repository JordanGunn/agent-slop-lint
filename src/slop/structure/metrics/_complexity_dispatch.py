"""Shared per-scope dispatch for the complexity.* metrics.

cyclomatic, cognitive, and combinatorial all follow the same pattern:
read per-scope thresholds from ``rule_config.params['thresholds']``,
iterate function callables or class-aggregate via ``_class_index``,
and emit a ``Slop`` per finding tagged with its emission scope.

``_function_slop`` constructs the function-scope finding;
``_run_complexity_metric`` is the shared body called by each metric's
``run_<name>`` function with a per-metric compute function and message
formatter.
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from slop.linter.rule_config import RuleConfig
from slop.config import Config
from slop.linter.slop import Slop
from slop.linter.types import RuleResult
from slop.structure.metrics._class_index import _class_index, _slop

if TYPE_CHECKING:
    from slop.structure.view import Structure


def _function_slop(
    rule: str, c, root: Path, severity: str, value: int, threshold: int,
    message: str,
) -> Slop:
    """Build a function-scope Slop finding."""
    try:
        rel = str(c.path.relative_to(root))
    except ValueError:
        rel = str(c.path)
    return Slop(
        rule=rule,
        file=rel,
        line=c.line,
        symbol=c.qualname.split(".")[-1],
        message=message,
        severity=severity,
        value=value,
        threshold=threshold,
        metadata={"end_line": c.end_line, "qualname": c.qualname},
        scope="function",
    )


def _run_complexity_metric(
    *,
    rule_name: str,
    structure: Structure,
    rule_config: RuleConfig,
    slop_config: Config,
    function_compute,
    class_aggregate,
    function_msg,
    class_msg,
) -> RuleResult:
    """Per-scope dispatch shared by complexity metrics.

    Function-scope threshold key (``thresholds.function``) gates the
    per-callable check via ``function_compute``; class-scope threshold
    key (``thresholds.class``) gates the per-class aggregate via
    ``class_aggregate``. Missing scope key in ``thresholds`` skips that
    scope entirely.
    """
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
            value = function_compute(c)
            if value > fn_threshold:
                findings.append((value, _function_slop(
                    rule_name, c, root, severity, value, fn_threshold,
                    function_msg(value, fn_threshold),
                )))

    cls_threshold = thresholds.get("class")
    if cls_threshold:
        groups, _, _, _ = _class_index(structure)
        for canonical, members in groups:
            classes_checked += 1
            agg = sum(class_aggregate(m) for m in members)
            if agg > cls_threshold:
                slop = _slop(
                    rule_name, canonical, root, severity, agg, cls_threshold,
                    class_msg(agg, cls_threshold),
                )
                slop.scope = "class"
                findings.append((agg, slop))

    findings.sort(key=lambda t: -t[0])
    violations = [s for _, s in findings]

    return RuleResult(
        rule=rule_name,
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "functions_checked": functions_checked,
            "classes_checked": classes_checked,
            "violation_count": len(violations),
        },
    )
