"""Orphan detection — top-level symbols with zero external references.

Redesign note: the legacy shelled out to ripgrep because the view did not retain
file contents. The carved corpus already holds every module's bytes, so we count
references in-memory — same signal, no subprocess, no external dependency. This
is a deliberate improvement, not a port of the rg plumbing.

Advisory by nature (the legacy emits it as an observation): static analysis can't
see plugin registration, reflection, or cross-language calls. Confidence
heuristics (short names, common verbs, dynamic languages, dunders) are ported.
"""
from __future__ import annotations

import re
from typing import Any

from ...identity import CallableKind, ScopeKind
from .records import Orphan

_COMMON_NAMES = frozenset({
    "run", "main", "setup", "init", "start", "stop", "get", "set",
    "update", "create", "delete", "load", "save", "process",
    "execute", "handle", "build", "parse", "check", "validate",
})


def orphans(corpus: Any) -> list[Orphan]:
    """Top-level callables/classes referenced in no file other than their own."""
    # Per-file text, once.
    texts: dict[str, str] = {}
    for mod in _modules(corpus):
        for f in mod.files:
            texts.setdefault(str(f), mod._content.decode("utf-8", errors="replace"))

    out: list[Orphan] = []
    for mod in _modules(corpus):
        def_path = str(mod.files[0]) if mod.files else ""
        for sym in mod.children():
            if not _is_top_level_symbol(sym):
                continue
            name = sym.name
            external = sum(
                _word_count(text, name)
                for path, text in texts.items()
                if path != def_path
            )
            if external == 0:
                confidence = _confidence(name, sym._grammar)
                out.append(Orphan(qualname=sym.qualname, kind=sym.KIND.name.lower(),
                                  confidence=confidence, locus=sym.id, line=sym.line))
    return out


def _is_top_level_symbol(sym: Any) -> bool:
    if sym.KIND == ScopeKind.CLASS:
        return True
    return sym.KIND == ScopeKind.CALLABLE and sym.kind == CallableKind.FUNCTION


def _word_count(text: str, word: str) -> int:
    return len(re.findall(r"\b" + re.escape(word) + r"\b", text))


def _confidence(symbol: str, grammar: Any) -> str:
    if grammar is not None and grammar.is_special_method(symbol):
        return "low"
    score = 3
    n = len(symbol)
    if n <= 4:
        score -= 2
    elif n <= 7:
        score -= 1
    if symbol.lower() in _COMMON_NAMES:
        score -= 2
    if grammar is not None and grammar.is_dynamic_language():
        score -= 1
    return "high" if score >= 3 else "medium" if score >= 1 else "low"


def _modules(component: Any):
    if component.KIND == ScopeKind.MODULE:
        yield component
        return
    for ch in component.children():
        yield from _modules(ch)
