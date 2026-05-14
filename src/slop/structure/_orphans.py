"""Orphans compute — symbols with zero detected external references.

Enumerates definitions from a ``Structure`` view (callables + named
scopes) and uses ``grep_kernel`` to count references in OTHER files
(definition file excluded). Confidence is heuristic — short names and
common verbs (``run`` / ``main`` / ``get``) get downgraded because
they collide with unrelated identifiers; dynamic languages
(Python / JavaScript / Ruby) also lose a confidence step because
reflection and dynamic dispatch can't be detected statically.

Every candidate carries the advisory caveat that static analysis can't
see plugin registration, cross-language calls, or runtime patching;
the rule layer renders this prominently so action requires human
verification.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from slop._text.grep import grep_kernel
from slop.structure.records import OrphanCandidate
from slop.tree.records import CallableKind, ScopeKind

if TYPE_CHECKING:
    from slop.structure.view import Structure


_COMMON_NAMES = frozenset({
    "run", "main", "setup", "init", "start", "stop", "get", "set",
    "update", "create", "delete", "load", "save", "process",
    "execute", "handle", "build", "parse", "check", "validate",
})

_DYNAMIC_LANGUAGES = frozenset({"python", "javascript", "ruby"})


def _compute_confidence(
    symbol: str, symbol_type: str, language: str | None,
) -> tuple[str, tuple[str, ...]]:
    """Heuristic confidence for an unreferenced-symbol candidate."""
    del symbol_type  # currently unused; kept for parity with the legacy kernel
    caveats: list[str] = []

    # Dunder methods can be runtime-dispatched (Python descriptor
    # protocol, __init_subclass__, etc.). Always low confidence.
    if symbol.startswith("__") and symbol.endswith("__"):
        return "low", (
            "dunder method — may be invoked by runtime, not visible in source",
        )

    score = 3
    n = len(symbol)
    if n <= 4:
        caveats.append(f"short name ({n} chars) — high false-positive risk")
        score -= 2
    elif n <= 7:
        caveats.append(
            f"short-medium name ({n} chars) — may match unrelated symbols"
        )
        score -= 1

    if symbol.lower() in _COMMON_NAMES:
        caveats.append(
            f"common name '{symbol}' — likely to match unrelated identifiers"
        )
        score -= 2

    if language in _DYNAMIC_LANGUAGES:
        caveats.append(
            f"{language}: reflection and dynamic dispatch cannot be detected statically"
        )
        score -= 1

    if score >= 3:
        confidence = "high"
    elif score >= 1:
        confidence = "medium"
    else:
        confidence = "low"
    return confidence, tuple(caveats)


def _word_match_count(text: str, word: str) -> int:
    """Count word-boundary occurrences of ``word`` in ``text``."""
    return len(re.findall(r"\b" + re.escape(word) + r"\b", text))


@dataclass
class _Definition:
    symbol: str
    symbol_type: str
    file: Path
    line: int
    language: str | None


def _enumerate_definitions(structure: Structure) -> list[_Definition]:
    """Yield one definition per top-level callable + named class scope.

    Methods (callables whose parent is a class scope) and nested
    functions are skipped — they don't bind a corpus-visible name in
    most languages, and reference-counting on them is high
    false-positive (matches every property access on every object).
    """
    defs: list[_Definition] = []
    seen: set[tuple[str, str]] = set()

    callables_by_qualname = {c.qualname for c in structure.callables()}
    scope_qualnames = {s.qualname for s in structure.scopes()}

    for c in structure.callables():
        # Skip methods, nested functions, lambdas
        if c.kind == CallableKind.METHOD:
            continue
        if c.parent in callables_by_qualname:
            continue  # nested function
        simple = c.qualname.split(".")[-1]
        if simple.startswith("<"):
            continue  # <lambda>, <anonymous>
        key = (simple, str(c.path))
        if key in seen:
            continue
        seen.add(key)
        defs.append(_Definition(
            symbol=simple,
            symbol_type="function",
            file=Path(c.path),
            line=c.line,
            language=structure.language_for(c),
        ))

    for s in structure.scopes():
        if s.kind not in (
            ScopeKind.CLASS, ScopeKind.INTERFACE, ScopeKind.STRUCT,
            ScopeKind.TRAIT,
        ):
            continue
        simple = s.qualname.split(".")[-1]
        if simple.startswith("<"):
            continue
        key = (simple, str(s.path))
        if key in seen:
            continue
        seen.add(key)
        defs.append(_Definition(
            symbol=simple,
            symbol_type={
                ScopeKind.CLASS: "class",
                ScopeKind.INTERFACE: "interface",
                ScopeKind.STRUCT: "struct",
                ScopeKind.TRAIT: "trait",
            }.get(s.kind, "class"),
            file=Path(s.path),
            line=s.line,
            language=structure.language_for(s),
        ))
    del scope_qualnames
    return defs


@dataclass(frozen=True)
class OrphansComputeResult:
    candidates: tuple[OrphanCandidate, ...]
    symbols_analyzed: int
    errors: tuple[str, ...]


def compute_orphans(
    structure: Structure,
    root: Path,
    *,
    min_name_length: int = 4,
    max_refs: int = 0,
) -> OrphansComputeResult:
    """Enumerate definitions and flag those with no external references.

    Args:
        structure: Parsed corpus view.
        root: Search root for ripgrep (typically the project root).
        min_name_length: Skip definitions whose simple name is shorter
            than this (short names collide with unrelated identifiers
            too readily for a meaningful signal).
        max_refs: Flag candidates with at most this many external
            references. 0 (default) means zero-reference only.
    """
    definitions = _enumerate_definitions(structure)
    definitions = [d for d in definitions if len(d.symbol) >= min_name_length]

    # All known source files in the corpus — we need them so grep can
    # exclude the def's own file via the search-list complement.
    all_paths = {Path(c.path) for c in structure.callables()}
    all_paths |= {Path(s.path) for s in structure.scopes()}
    all_paths = {p for p in all_paths if p.exists()}

    errors: list[str] = []
    candidates: list[OrphanCandidate] = []

    for d in definitions:
        others = [p for p in all_paths if p != d.file]
        if not others:
            external_refs = 0
        else:
            grep_result = grep_kernel(
                patterns=[{"kind": "fixed", "value": d.symbol}],
                root=root,
                files=others,
                mode="fixed",
                case="sensitive",
            )
            errors.extend(grep_result.errors)
            external_refs = sum(
                _word_match_count(m.content, d.symbol)
                for m in grep_result.matches
            )

        if external_refs > max_refs:
            continue

        confidence, caveats = _compute_confidence(
            d.symbol, d.symbol_type, d.language,
        )
        candidates.append(OrphanCandidate(
            symbol=d.symbol,
            symbol_type=d.symbol_type,
            file=str(d.file),
            line=d.line,
            external_refs=external_refs,
            confidence=confidence,
            caveats=caveats,
        ))

    return OrphansComputeResult(
        candidates=tuple(candidates),
        symbols_analyzed=len(definitions),
        errors=tuple(errors),
    )
