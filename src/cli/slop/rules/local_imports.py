"""Local import rule — wraps the local_imports_kernel.

Rules:
  structural.local_imports  — flag import statements inside function bodies

Function-scoped imports are invisible to slop's dependency (deps) kernel,
which only walks module-level imports.  They also impose a repeated import
machinery cost on every call and make dependency audits harder.

Legitimate exceptions (conditional platform imports, optional-dependency
try/except blocks) can be waived individually via ``[[waivers]]`` in
``.slop.toml``.
"""

from __future__ import annotations

from pathlib import Path

from slop._structural.local_imports import local_imports_kernel
from slop.models import RuleConfig, RuleResult, SlopConfig, Violation


def run_local_imports(
    root: Path, rule_config: RuleConfig, slop_config: SlopConfig
) -> RuleResult:
    """Flag import statements whose nearest enclosing ancestor is a function."""
    severity = rule_config.severity
    # A threshold > 0 allows callers to tolerate some local imports per file.
    threshold: int = rule_config.params.get("threshold", 0)

    result = local_imports_kernel(
        root=root,
        excludes=slop_config.exclude or None,
    )

    violations: list[Violation] = []
    # Group by file so we can apply a per-file threshold.
    by_file: dict[str, list] = {}
    for li in result.local_imports:
        by_file.setdefault(li.file, []).append(li)

    for file_path, items in by_file.items():
        if len(items) <= threshold:
            continue
        for li in items:
            violations.append(
                Violation(
                    rule="structural.local_imports",
                    file=file_path,
                    line=li.line,
                    symbol=li.function,
                    message=(
                        f"import inside function '{li.function}': {li.module}"
                    ),
                    severity=severity,
                    value=len(items),
                    threshold=threshold,
                    metadata={
                        "module": li.module,
                        "language": li.language,
                        "function": li.function,
                    },
                )
            )

    return RuleResult(
        rule="structural.local_imports",
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "files_searched": result.files_searched,
            "local_imports_found": len(result.local_imports),
            "violation_count": len(violations),
        },
        errors=list(result.errors),
    )
