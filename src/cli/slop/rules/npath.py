"""NPath rule — wraps slop._aux npath_kernel.

Rule:
  npath  — fail if any function's acyclic execution-path count exceeds threshold

NPath (Nejmeh 1988) counts acyclic execution paths. Unlike McCabe's CCX
(additive: 1 + branches), NPath is multiplicative — sequential branches
multiply path counts. This catches combinatorial explosion that CCX
underreports. Example: 10 sequential ifs produce CCX=11 but NPath=1024.
"""

from __future__ import annotations

from pathlib import Path

from slop._aux.kernels.npath import npath_kernel
from slop.models import RuleConfig, RuleResult, SlopConfig, Violation


def run_npath(root: Path, rule_config: RuleConfig, slop_config: SlopConfig) -> RuleResult:
    """Check NPath acyclic execution path count per function against threshold."""
    threshold = rule_config.params.get("npath_threshold", 200)
    severity = rule_config.severity

    result = npath_kernel(
        root=root,
        languages=slop_config.languages or None,
        excludes=slop_config.exclude or None,
    )

    violations: list[Violation] = []
    for fn in result.functions:
        if fn.npath > threshold:
            violations.append(
                Violation(
                    rule="npath",
                    file=fn.file,
                    line=fn.line,
                    symbol=fn.name,
                    message=f"NPath {fn.npath} exceeds {threshold}",
                    severity=severity,
                    value=fn.npath,
                    threshold=threshold,
                    metadata={"end_line": fn.end_line, "language": fn.language},
                )
            )

    return RuleResult(
        rule="npath",
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "functions_checked": result.functions_analyzed,
            "violation_count": len(violations),
        },
        errors=list(result.errors),
    )
