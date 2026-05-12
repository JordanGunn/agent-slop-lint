"""Cowards kernel — flag identifiers ending in disambiguator suffixes.

Detects names ending in numeric suffixes (``result1``, ``attempt_2``,
``_v3``) or alphabetic disambiguators (``_old``, ``_new``, ``_local``,
``_alt``, ``_inner``, ``_helper``, ``_temp``).

These are the artifact of failure to commit. Two related things
exist; instead of picking one or describing what differs, both
are kept with arbitrary disambiguating suffixes. The suffix is
provenance collapse — it marks the codebase's inability to decide.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from slop._lexical._naming import enumerate_functions


# Numeric suffix patterns
_NUMERIC_PATTERNS = [
    re.compile(r"^(?P<stem>.+?)_?(?P<digit>\d+)$"),         # result1, attempt_2
    re.compile(r"^(?P<stem>.+?)_v(?P<digit>\d+)$"),          # _v1
    re.compile(r"^(?P<stem>.+?)_attempt(?P<digit>\d+)$"),    # _attempt1
]

# Alphabetic disambiguator suffixes (after underscore)
DEFAULT_ALPHA_SUFFIXES: frozenset[str] = frozenset({
    "old", "new", "local", "inner", "alt", "helper", "temp", "tmp",
    "copy", "backup", "orig", "original",
})


@dataclass
class NumberedVariant:
    name: str
    file: str
    line: int
    language: str
    suffix: str         # the matched suffix (e.g. "_2", "_old")
    kind: str           # "numeric" or "alphabetic"


@dataclass
class CowardsResult:
    items: list[NumberedVariant] = field(default_factory=list)
    files_searched: int = 0
    functions_analyzed: int = 0
    errors: list[str] = field(default_factory=list)


def cowards_kernel(
    root: Path,
    *,
    languages: list[str] | None = None,
    globs: list[str] | None = None,
    excludes: list[str] | None = None,
    hidden: bool = False,
    no_ignore: bool = False,
    alpha_suffixes: frozenset[str] = DEFAULT_ALPHA_SUFFIXES,
    min_stem_tokens: int = 1,
) -> CowardsResult:
    """Flag function names matching disambiguation-suffix patterns.

    ``min_stem_tokens`` filters out single-letter prefixes (``a1``,
    ``x2``) which are typically loop variables, not disambiguated
    helpers.
    """
    items: list[NumberedVariant] = []
    files_set: set[str] = set()
    fn_count = 0

    for ctx in enumerate_functions(
        root,
        languages=languages, globs=globs, excludes=excludes,
        hidden=hidden, no_ignore=no_ignore,
    ):
        fn_count += 1
        files_set.add(ctx.file)
        if ctx.name.startswith("<"):
            continue

        match = _classify(ctx.name, alpha_suffixes, min_stem_tokens)
        if match is None:
            continue
        suffix, kind = match
        items.append(NumberedVariant(
            name=ctx.name, file=ctx.file, line=ctx.line,
            language=ctx.language, suffix=suffix, kind=kind,
        ))

    return CowardsResult(
        items=items,
        files_searched=len(files_set),
        functions_analyzed=fn_count,
        errors=[],
    )


def _classify(
    name: str,
    alpha_suffixes: frozenset[str],
    min_stem_tokens: int,
) -> tuple[str, str] | None:
    """Return ``(suffix, kind)`` if name matches a disambiguator pattern,
    else None."""
    stripped = name.strip("_")
    if not stripped:
        return None

    # Numeric: result1, attempt_2, _v1
    for pattern in _NUMERIC_PATTERNS:
        m = pattern.match(stripped)
        if m is not None:
            stem = m.group("stem")
            digit = m.group("digit")
            stem_tokens = [t for t in stem.split("_") if t]
            if len(stem_tokens) < min_stem_tokens:
                continue
            return (f"_{digit}" if "_" in stripped[len(stem):] else digit,
                    "numeric")

    # Alphabetic: needs an underscore separator and a recognised suffix
    if "_" in stripped:
        last = stripped.rsplit("_", 1)[1].lower()
        stem = stripped.rsplit("_", 1)[0]
        stem_tokens = [t for t in stem.split("_") if t]
        if last in alpha_suffixes and len(stem_tokens) >= min_stem_tokens:
            return (f"_{last}", "alphabetic")

    return None
