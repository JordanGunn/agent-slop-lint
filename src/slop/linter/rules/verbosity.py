"""lexical.verbosity — flag entity names exceeding N word-tokens.

A long function or class name is usually a class-without-class:
``check_required_binaries`` is three tokens because the namespace it
should belong to doesn't exist yet. The smell is structural — the
name compensates for missing scope.
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from slop.linter.rule import Rule
from slop.config import Config
from slop.linter.slop import Slop
from slop.linter.types import RuleResult
from slop.linter.tags import Tag
from slop.linter.types import RuleDefinition

if TYPE_CHECKING:
    from slop.lexicon.view import Lexicon


def run_verbosity(
    lexicon: Lexicon, rule_config: Rule, slop_config: Config,
) -> RuleResult:
    """Flag named entities whose token-split exceeds the threshold."""
    max_tokens = int(rule_config.params.get("max_tokens", 3))
    check_classes = bool(rule_config.params.get("check_classes", True))
    severity = rule_config.severity
    root = Path(slop_config.root).expanduser().resolve() if slop_config.root else None

    violations: list[Slop] = []
    analyzed = 0
    for entity in lexicon.named_entities():
        analyzed += 1
        if entity.kind == "class" and not check_classes:
            continue
        if len(entity.tokens) <= max_tokens:
            continue
        file = entity.file
        if root is not None:
            try:
                file = str(Path(entity.file).relative_to(root))
            except ValueError:
                pass
        violations.append(Slop(
            rule="lexical.verbosity",
            file=file,
            line=entity.line,
            symbol=entity.name,
            message=(
                f"{entity.kind} '{entity.name}' has {len(entity.tokens)} tokens "
                f"(threshold {max_tokens}): {list(entity.tokens)}"
            ),
            severity=severity,
            value=len(entity.tokens),
            threshold=max_tokens,
            metadata={
                "kind": entity.kind,
                "tokens": list(entity.tokens),
                "language": entity.language,
            },
        ))

    return RuleResult(
        rule="lexical.verbosity",
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "entities_analyzed": analyzed,
            "violation_count": len(violations),
            "check_classes": check_classes,
        },
    )

RULE = RuleDefinition(
    name=Tag.VERBOSITY.key,
    category=Tag.VERBOSITY.key,
    description='Function/class names with too many word-tokens (missing namespace)',
    default_severity='warning',
    default_enabled=True,
    threshold_label='> 3 tokens',
    run=run_verbosity,
)
