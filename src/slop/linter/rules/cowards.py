"""lexical.cowards — flag identifiers ending in disambiguator suffixes.

The artifact of failure to commit: ``_v1`` / ``_v2``, ``_old`` /
``_new``, ``_local`` / ``_alt``. The codebase couldn't pick one, so
it kept both, marked with arbitrary suffixes that obscure what
actually differs.
"""
from __future__ import annotations

import re
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


# Numeric suffix patterns. Cover trailing digits with optional
# underscore separation, ``_v<n>`` version markers, and ``_attempt<n>``
# trial markers.
_NUMERIC_PATTERNS = [
    re.compile(r"^(?P<stem>.+?)_?(?P<digit>\d+)$"),
    re.compile(r"^(?P<stem>.+?)_v(?P<digit>\d+)$"),
    re.compile(r"^(?P<stem>.+?)_attempt(?P<digit>\d+)$"),
]

DEFAULT_ALPHA_SUFFIXES: frozenset[str] = frozenset({
    "old", "new", "local", "inner", "alt", "helper", "temp", "tmp",
    "copy", "backup", "orig", "original",
})


def _classify(
    name: str, alpha_suffixes: frozenset[str], min_stem_tokens: int,
) -> tuple[str, str] | None:
    """Return ``(suffix, kind)`` if name matches a disambiguator pattern."""
    stripped = name.strip("_")
    if not stripped:
        return None
    for pattern in _NUMERIC_PATTERNS:
        m = pattern.match(stripped)
        if m is not None:
            stem = m.group("stem")
            digit = m.group("digit")
            stem_tokens = [t for t in stem.split("_") if t]
            if len(stem_tokens) < min_stem_tokens:
                continue
            return (
                f"_{digit}" if "_" in stripped[len(stem):] else digit,
                "numeric",
            )
    if "_" in stripped:
        last = stripped.rsplit("_", 1)[1].lower()
        stem = stripped.rsplit("_", 1)[0]
        stem_tokens = [t for t in stem.split("_") if t]
        if last in alpha_suffixes and len(stem_tokens) >= min_stem_tokens:
            return (f"_{last}", "alphabetic")
    return None


def run_cowards(
    lexicon: Lexicon, rule_config: Rule, slop_config: Config,
) -> RuleResult:
    """Flag function names matching disambiguation-suffix patterns."""
    raw_alpha = rule_config.params.get("alpha_suffixes")
    alpha_suffixes = (
        frozenset(s.lower() for s in raw_alpha)
        if raw_alpha is not None
        else DEFAULT_ALPHA_SUFFIXES
    )
    min_stem_tokens = int(rule_config.params.get("min_stem_tokens", 1))
    severity = rule_config.severity
    root = Path(slop_config.root).expanduser().resolve() if slop_config.root else None

    violations: list[Slop] = []
    functions_checked = 0
    for entity in lexicon.named_entities():
        if entity.kind != "function":
            continue
        functions_checked += 1
        hit = _classify(entity.name, alpha_suffixes, min_stem_tokens)
        if hit is None:
            continue
        suffix, kind = hit
        file = entity.file
        if root is not None:
            try:
                file = str(Path(entity.file).relative_to(root))
            except ValueError:
                pass
        violations.append(Slop(
            rule="lexical.cowards",
            file=file,
            line=entity.line,
            symbol=entity.name,
            message=(
                f"function `{entity.name}` ends in disambiguator `{suffix}` "
                f"({kind}); the codebase couldn't commit — either pick one "
                f"or describe what differs"
            ),
            severity=severity,
            metadata={
                "suffix": suffix,
                "kind": kind,
                "language": entity.language,
            },
        ))

    return RuleResult(
        rule="lexical.cowards",
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "functions_checked": functions_checked,
            "violation_count": len(violations),
        },
    )

RULE = RuleDefinition(
    name=Tag.COWARDS.key,
    category=Tag.COWARDS.key,
    description='Identifiers ending in disambiguator suffixes (_1, _v2, _old, _new, _local) — provenance collapse',
    default_severity='warning',
    default_enabled=True,
    threshold_label='any match',
    run=run_cowards,
)
