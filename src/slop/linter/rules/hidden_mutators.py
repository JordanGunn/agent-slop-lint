"""Hidden-mutator rule — flag functions that mutate parameters in place.

Rules:
  ``types.hidden_mutators``  — flag functions that mutate
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

from slop.linter.tags import Tag
from slop.linter.rule import Rule
from slop.config import Config
from slop.linter.slop import Slop
from slop.linter.types import RuleResult
from slop.linter.types import RuleDefinition

if TYPE_CHECKING:
    from slop.structure.view import Structure


_RULE = Tag.HIDDEN_MUTATORS.key

def run(
    structure: Structure, rule_config: Rule, slop_config: Config,
) -> RuleResult:
    """Flag functions that mutate their parameters in place (function scope)."""
    del slop_config
    require_annotation = bool(
        rule_config.params.get("require_type_annotation", True),
    )
    thresholds = rule_config.params.get("thresholds", {}) or {}
    min_mutations = int(thresholds.get("function", 1))
    severity = rule_config.severity

    entries = structure.hidden_mutators(
        require_type_annotation=require_annotation,
    )

    violations: list[Slop] = []
    if "function" in thresholds:
        for entry in entries:
            if entry.mutation_count < min_mutations:
                continue
            mutated = sorted({m.param_name for m in entry.mutations})
            methods = sorted({m.method for m in entry.mutations})
            violations.append(Slop(
                rule=_RULE,
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
                scope="function",
            ))

    return RuleResult(
        rule=_RULE,
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "callables_analyzed": len(entries),
            "violations": len(violations),
            "require_type_annotation": require_annotation,
        },
    )

RULE = RuleDefinition(
    name=_RULE,
    category=_RULE,
    description='Functions that mutate collection-typed parameters in place',
    default_severity='warning',
    default_enabled=True,
    threshold_label='any mutation',
    run=run,
    scopes=('function',),
)
