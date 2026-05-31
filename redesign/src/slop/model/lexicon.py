"""Concrete Lexicon projection — the cleaned identifier token-space over an
extent. Derived from the component's AST identifiers unioned with the fs-derived
component names (module/package/realm), then split (camel/snake), lowercased,
and noise-stripped. Tokenizer + UNIVERSAL_NOISE ported from the legacy.
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Any

from ..component.identity import ComponentKind, Extent

_CAMEL_LOWER_UPPER = re.compile(r"([a-z])([A-Z])")
_CAMEL_UPPER_TITLE = re.compile(r"([A-Z]+)([A-Z][a-z])")

# Newman et al. (SANER 2017) 14 + English glue. SE-boilerplate (manager/helper)
# is deliberately NOT noise — that is the signal the lexical 'hammers' rule wants.
_NEWMAN_14 = frozenset({
    "a", "length", "id", "pos", "start", "next", "str", "key",
    "f", "x", "index", "p", "left", "result",
})
_GLUE = frozenset({
    "the", "an", "is", "are", "to", "for", "in", "on", "of",
    "with", "by", "as", "at", "and", "or", "but", "if",
})
UNIVERSAL_NOISE = _NEWMAN_14 | _GLUE

_FS_NAMED = (ComponentKind.MODULE, ComponentKind.PACKAGE, ComponentKind.REALM)


def split_tokens(name: str) -> tuple[str, ...]:
    """Split an identifier into word tokens (snake_case + CamelCase aware)."""
    cleaned = name.strip("_")
    cleaned = _CAMEL_LOWER_UPPER.sub(r"\1_\2", cleaned)
    cleaned = _CAMEL_UPPER_TITLE.sub(r"\1_\2", cleaned)
    return tuple(p for p in re.split(r"[_\d]+", cleaned) if p)


class Lexicon:
    """Implements ``slop.component.projection.Lexicon``. Holds (raw-name, path)
    sources; tokenises lazily-eagerly on construction."""

    def __init__(self, sources: list[tuple[str, Any]]) -> None:
        self._sources = sources
        self._tokens: list[tuple[str, Any]] = []
        for raw, path in sources:
            for tok in split_tokens(raw):
                low = tok.lower()
                if low and low not in UNIVERSAL_NOISE:
                    self._tokens.append((low, path))
        self._counter: Counter[str] = Counter(t for t, _ in self._tokens)

    def tokens(self) -> tuple[str, ...]:
        """Distinct significant tokens, sorted."""
        return tuple(sorted(self._counter))

    def significant_token_count(self) -> int:
        return len(self._counter)

    def hapax_ratio(self) -> float:
        n = len(self._counter)
        if n == 0:
            return 0.0
        return sum(1 for c in self._counter.values() if c == 1) / n

    def slice(self, extent: Extent) -> "Lexicon":
        paths = {span.path for span in extent.spans}
        return Lexicon([(r, p) for r, p in self._sources if p is not None and str(p) in paths])


def build_lexicon(component: Any) -> Lexicon:
    """Build a Lexicon over a component: AST identifiers ∪ fs-derived names."""
    sources: list[tuple[str, Any]] = []
    for node, content, path in component.ast().walk():
        t = node.type
        if t == "identifier" or t.endswith("_identifier"):
            sources.append((content[node.start_byte:node.end_byte].decode("utf-8", errors="replace"), path))
    for comp in _iter_all(component):
        if comp.KIND in _FS_NAMED:
            sources.append((comp.name, comp.files[0] if comp.files else None))
    return Lexicon(sources)


def _iter_all(component: Any):
    yield component
    for ch in component.children():
        yield from _iter_all(ch)
