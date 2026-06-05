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
from collections import Counter
from typing import Any

from ...identity import CallableKind, ScopeKind
from .records import Orphan

_WORD = re.compile(r"\w+")

_COMMON_NAMES = frozenset({
    "run", "main", "setup", "init", "start", "stop", "get", "set",
    "update", "create", "delete", "load", "save", "process",
    "execute", "handle", "build", "parse", "check", "validate",
})


def orphans(corpus: Any) -> list[Orphan]:
    """Top-level callables/classes referenced in no file other than their own.

    A symbol is an orphan when its name appears as a whole word in no file but the one
    that defines it. Identifiers are ``\\w+`` runs, so a ``\\bname\\b`` occurrence is
    exactly a word token equal to ``name``: tokenise each file into a word-count
    ``Counter`` once, then each symbol's external-reference count is
    ``total[name] - in_def_file[name]`` — two dict lookups. (The previous form recompiled
    a per-name regex and rescanned every file's full text for every symbol — O(symbols ×
    files × filesize), ~60s on the slop corpus.)
    """
    # Per-file text, then per-file word counts, once.
    texts: dict[str, str] = {}
    for mod in _modules(corpus):
        for f in mod.files:
            texts.setdefault(str(f), mod._content.decode("utf-8", errors="replace"))
    file_counts: dict[str, Counter] = {p: Counter(_WORD.findall(t)) for p, t in texts.items()}
    total: Counter = Counter()
    for counts in file_counts.values():
        total.update(counts)

    out: list[Orphan] = []
    for mod in _modules(corpus):
        def_path = str(mod.files[0]) if mod.files else ""
        in_def = file_counts.get(def_path)
        for sym in mod.children():
            if not _is_top_level_symbol(sym):
                continue
            name = sym.name
            external = total.get(name, 0) - (in_def.get(name, 0) if in_def else 0)
            if external == 0:
                confidence = _confidence(name, sym._grammar)
                out.append(Orphan(qualname=sym.qualname, kind=sym.KIND.name.lower(),
                                  confidence=confidence, locus=sym.id, line=sym.line))
    return out


def _is_top_level_symbol(sym: Any) -> bool:
    if sym.KIND == ScopeKind.CLASS:
        return True
    return sym.KIND == ScopeKind.CALLABLE and sym.kind == CallableKind.FUNCTION


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
