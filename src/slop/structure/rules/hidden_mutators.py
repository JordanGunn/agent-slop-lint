"""Hidden-mutator rule — flag functions that mutate parameters in place.

Rules:
  ``structural.types.hidden_mutators``  — flag functions that mutate
    collection-typed parameters in place (``.append``, ``.extend``,
    ``.add``, ``.update``, …) or pointer/reference parameters
    (``*p = X``, ``p->x = Y``, ``p = ...`` on a non-const reference).

Mutating a passed-in collection or reference is an out-parameter
pattern: the caller's data is silently modified as a side effect.
It makes call-site reasoning harder, prevents pure-functional
testing, and often signals that the function should return a new
value instead.

Config params
-------------
  require_type_annotation  bool  When True (default), only flag
                                 parameters with explicit collection-
                                 type annotations.
  min_mutations            int   Minimum number of mutation events in
                                 a function before flagging it
                                 (default: 1).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from slop.config.models import RuleConfig, SlopConfig
from slop.linter.slop import Slop
from slop.linter.types import RuleResult

if TYPE_CHECKING:
    from slop.structure.view import Structure


def run_hidden_mutators(
    structure: Structure, rule_config: RuleConfig, slop_config: SlopConfig,
) -> RuleResult:
    """Flag functions that mutate their parameters in place."""
    del slop_config
    require_annotation = bool(
        rule_config.params.get("require_type_annotation", True),
    )
    min_mutations = int(rule_config.params.get("min_mutations", 1))
    severity = rule_config.severity

    entries = structure.hidden_mutators(
        require_type_annotation=require_annotation,
    )

    violations: list[Slop] = []
    for entry in entries:
        if entry.mutation_count < min_mutations:
            continue
        mutated = sorted({m.param_name for m in entry.mutations})
        methods = sorted({m.method for m in entry.mutations})
        violations.append(Slop(
            rule="structural.types.hidden_mutators",
            file=entry.file,
            line=entry.line,
            symbol=entry.function_name,
            message=(
                f"'{entry.function_name}' mutates parameter(s) "
                f"{', '.join(mutated)} "
                f"via {', '.join(f'.{m}()' for m in methods)}"
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
                "mutated_params": mutated,
            },
        ))

    return RuleResult(
        rule="structural.types.hidden_mutators",
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "callables_analyzed": len(entries),
            "violations": len(violations),
            "require_type_annotation": require_annotation,
        },
    )
