"""Dependencies rules — wraps the vendored deps_kernel.

Rules:
  deps  — fail if any dependency cycles exist

The Acyclic Dependencies Principle (Lakos 1996; Martin 2002, ch. 20) holds
that import cycles prevent independent reasoning about, testing of, or
extraction of any module in the cycle — every change touches the whole
loop. slop detects cycles via Tarjan's (1972) SCC algorithm on the import
graph, with tree-sitter extracting imports per language (regex fallback
when the parser fails).
"""

from __future__ import annotations

from pathlib import Path

from slop._aux.kernels.deps import deps_kernel
from slop.models import RuleConfig, RuleResult, SlopConfig, Violation


def run_cycles(
    root: Path, rule_config: RuleConfig, slop_config: SlopConfig
) -> RuleResult:
    """Check for dependency cycles."""
    fail_on_cycles = rule_config.params.get("fail_on_cycles", True)
    severity = rule_config.severity

    result = deps_kernel(
        root=root,
        excludes=slop_config.exclude or None,
    )

    violations: list[Violation] = []
    if fail_on_cycles and result.cycles:
        for cycle in result.cycles:
            cycle_str = " \u2192 ".join(cycle)
            violations.append(
                Violation(
                    rule="deps",
                    file=cycle[0] if cycle else "",
                    line=None,
                    symbol=None,
                    message=f"cycle: {cycle_str}",
                    severity=severity,
                    value=len(cycle),
                    threshold=0,
                    metadata={"cycle": cycle},
                )
            )

    return RuleResult(
        rule="deps",
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "files_analyzed": len(result.files),
            "cycles_found": len(result.cycles),
            "violation_count": len(violations),
        },
        errors=list(result.errors),
    )
