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
from slop.lexicon.affix import UNIVERSAL_NOISE
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

    # Distribution signals — used to classify whether verbosity reflects
    # scope-boundary failure (high-spread tokens propagating widely) or
    # local naming (tokens scoped to a single file).
    spread_map = {
        t: len(files)
        for t, files in lexicon.token_locations(exclude=UNIVERSAL_NOISE).items()
    }
    head_tokens = frozenset(
        t for t, _ in lexicon.frequency_head(exclude=UNIVERSAL_NOISE)
    )

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

        # Per-token distribution profile.
        token_spreads = [
            spread_map.get(t.lower(), 0)
            for t in entity.tokens
            if t.lower() not in UNIVERSAL_NOISE
        ]
        head_count = sum(
            1 for t in entity.tokens if t.lower() in head_tokens
        )
        max_spread = max(token_spreads) if token_spreads else 0
        mean_spread = (
            sum(token_spreads) / len(token_spreads) if token_spreads else 0.0
        )

        # Scope-leak heuristic: most tokens are widely spread AND in the
        # frequency head. The name is shouldering disambiguation work that
        # the scope should be doing.
        is_scope_leak = (
            mean_spread >= 5.0 and head_count >= len(entity.tokens) // 2
        )

        if is_scope_leak:
            advice = (
                f"tokens are high-spread (mean spread {mean_spread:.0f} "
                f"files, {head_count}/{len(entity.tokens)} in frequency "
                f"head) — the scope is too loose, not the name too long. "
                f"Consider whether `{entity.name}` belongs in a narrower "
                f"namespace where some of these tokens are implicit."
            )
        else:
            advice = (
                f"tokens are locally scoped (mean spread "
                f"{mean_spread:.0f}) — verbosity is local, may just be "
                f"a long descriptive name."
            )

        violations.append(Slop(
            rule="lexical.verbosity",
            file=file,
            line=entity.line,
            symbol=entity.name,
            message=(
                f"{entity.kind} '{entity.name}' has {len(entity.tokens)} "
                f"tokens (threshold {max_tokens}): {list(entity.tokens)}. "
                f"{advice}"
            ),
            severity=severity,
            value=len(entity.tokens),
            threshold=max_tokens,
            metadata={
                "kind": entity.kind,
                "tokens": list(entity.tokens),
                "language": entity.language,
                "mean_token_spread": round(mean_spread, 1),
                "max_token_spread": max_spread,
                "tokens_in_head": head_count,
                "is_scope_leak": is_scope_leak,
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
