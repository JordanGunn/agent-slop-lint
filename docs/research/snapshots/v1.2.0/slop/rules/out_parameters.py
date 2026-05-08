"""Out-parameter mutation rule — wraps out_parameters_kernel.

Rules:
  structural.types.hidden_mutators  — flag functions that mutate collection-typed
                               parameters in place (.append, .extend, .add,
                               .update, etc.).

Mutating a passed-in collection is an "out-parameter" pattern: the caller's
data is silently modified as a side effect.  It makes call-site reasoning
harder, prevents pure functional testing, and often signals that the function
should instead return a new collection.

Config params
-------------
  require_type_annotation  bool   When True (default), only flag parameters
                                  with explicit collection type annotations
                                  (list, dict, set, etc.).
                                  When False, any mutated parameter is flagged.
  min_mutations            int    Minimum number of mutation calls in a function
                                  before flagging it (default: 1).
"""

from __future__ import annotations

from pathlib import Path

from slop._structural.out_parameters import out_parameters_kernel
from slop.models import RuleConfig, RuleResult, SlopConfig, Violation


def run_out_parameters(
    root: Path, rule_config: RuleConfig, slop_config: SlopConfig
) -> RuleResult:
    """Flag functions that mutate their collection-typed parameters."""
    require_annotation: bool = bool(
        rule_config.params.get("require_type_annotation", True)
    )
    min_mutations: int = int(rule_config.params.get("min_mutations", 1))
    severity = rule_config.severity

    result = out_parameters_kernel(
        root=root,
        languages=slop_config.languages or None,
        excludes=slop_config.exclude or None,
        require_type_annotation=require_annotation,
    )

    violations: list[Violation] = []
    for entry in result.entries:
        if entry.mutation_count < min_mutations:
            continue
        # Summarise which params were mutated and with which methods
        mutated_params = sorted({m.param_name for m in entry.mutations})
        methods_used = sorted({m.method for m in entry.mutations})
        violations.append(
            Violation(
                rule="structural.types.hidden_mutators",
                file=entry.file,
                line=entry.line,
                symbol=entry.name,
                message=(
                    f"'{entry.name}' mutates parameter(s) "
                    f"{', '.join(mutated_params)} "
                    f"via {', '.join(f'.{m}()' for m in methods_used)}"
                ),
                severity=severity,
                value=entry.mutation_count,
                threshold=min_mutations,
                metadata={
                    "language": entry.language,
                    "mutations": [
                        {"param": m.param_name, "method": m.method, "line": m.line}
                        for m in entry.mutations
                    ],
                    "mutated_params": mutated_params,
                },
            )
        )

    return RuleResult(
        rule="structural.types.hidden_mutators",
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "functions_analyzed": result.functions_analyzed,
            "files_searched": result.files_searched,
            "violations": len(violations),
            "require_type_annotation": require_annotation,
        },
        errors=list(result.errors),
    )
