"""Lexical — slop's lexical-signal view over a region (the twin of ``Structure``).

Constructed ``Lexical.over(region)``. Where ``Structure`` reads control-flow and
coupling, ``Lexical`` reads the *naming* surface: entity and parameter vocabulary,
token spread across files, and the receiver/affix structure the lexical rules judge.

It computes from the scope tree directly (``region._iter_callables`` /
``_iter_classes`` + ``split_tokens``), not from the ``Lexicon`` token kernel: the
rules need the entity-vs-parameter partition and per-callable structure, which the
kernel (a flat role-tagged token bag) deliberately does not carry. The kernel remains
the home of pure whole-space lexicostatistics (Zipf/hapax); this view is the home of
the structure-aware lexical signals.
"""
from __future__ import annotations

from collections import Counter
from typing import Any

from ...identity import CallableKind
from ...lexicon.tokenize import split_tokens
from .records import NamedEntity


class Lexical:
    def __init__(self, region: Any) -> None:
        self._r = region

    @classmethod
    def over(cls, region: Any) -> "Lexical":
        return cls(region)

    # ---- scope-tree entity iteration --------------------------------------
    def _named_callables(self) -> list[Any]:
        return [c for c in self._r._iter_callables()
                if c.kind != CallableKind.LAMBDA and not c.name.startswith("<")]

    def _classes(self) -> list[Any]:
        return [c for c in self._r._iter_classes() if not c.name.startswith("<")]

    def callables(self) -> list[Any]:
        """Named (non-lambda) callables in the region."""
        return self._named_callables()

    def files(self) -> list[Any]:
        """Distinct source files in the region."""
        seen: dict[str, Any] = {}
        for c in self._named_callables() + self._classes():
            for f in c.files:
                seen.setdefault(str(f), f)
        return list(seen.values())

    def named_entities(self) -> list[NamedEntity]:
        """Token-split named callables (``kind="function"``) and classes
        (``kind="class"``). Consumed by verbosity / stutter / hammers."""
        out: list[NamedEntity] = []
        for c in self._named_callables():
            out.append(self._entity(c, "function"))
        for s in self._classes():
            out.append(self._entity(s, "class"))
        return [e for e in out if e is not None]

    def _entity(self, scope: Any, kind: str) -> NamedEntity | None:
        tokens = split_tokens(scope.name)
        if not tokens:
            return None
        return NamedEntity(
            name=scope.name, kind=kind,
            file=str(scope.files[0]) if scope.files else "",
            line=_line(scope), language=_language(scope), tokens=tokens,
        )

    # ---- token vocabulary: entity names + parameter names ------------------
    def _vocab_units(self) -> list[tuple[str, str]]:
        """Stream of ``(token, file)`` over the entity-name + parameter vocabulary —
        the legacy ``token_locations`` / ``frequency_head`` source (body identifiers
        excluded; those are a separate spread signal)."""
        units: list[tuple[str, str]] = []
        for c in self._named_callables():
            path = str(c.files[0]) if c.files else ""
            for tok in split_tokens(c.name):
                units.append((tok.lower(), path))
            for param in c.parameters():
                if param in ("self", "cls"):
                    continue
                for tok in split_tokens(param):
                    units.append((tok.lower(), path))
        for s in self._classes():
            path = str(s.files[0]) if s.files else ""
            for tok in split_tokens(s.name):
                units.append((tok.lower(), path))
        return units

    def token_locations(self) -> dict[str, set[str]]:
        """Token → set of files where it appears (entity + parameter vocabulary).
        The headline sprawl/imposters primitive: a token in many files with no module
        of that name is a missing-module candidate."""
        out: dict[str, set[str]] = {}
        for tok, path in self._vocab_units():
            out.setdefault(tok, set()).add(path)
        return out

    def frequencies(self) -> Counter:
        """Vocabulary token → occurrence count (entity + parameter names)."""
        return Counter(tok for tok, _ in self._vocab_units())

    def frequency_head(self, *, threshold: int | None = None) -> list[tuple[str, int]]:
        """Tokens with count ≥ ``threshold`` (default: 90th percentile), descending.
        The frequency-head cohort — high-prevalence vocabulary."""
        freq = self.frequencies()
        if not freq:
            return []
        if threshold is None:
            counts = sorted(freq.values())
            threshold = counts[max(0, int(0.9 * (len(counts) - 1)))]
        head = [(t, n) for t, n in freq.items() if n >= threshold]
        head.sort(key=lambda kv: (-kv[1], kv[0]))
        return head


def _line(scope: Any) -> int:
    node = getattr(scope, "_node", None)
    if node is not None and getattr(node, "start_point", None) is not None:
        return node.start_point[0] + 1
    return 0


def _language(scope: Any) -> str:
    grammar = getattr(scope, "_grammar", None)
    return grammar.id if grammar is not None else ""
