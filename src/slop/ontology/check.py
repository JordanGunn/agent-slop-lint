"""Integrity of a vocabulary: the SKOS conditions, plus one word for one term.

- Every label is a single word as it can appear in an identifier (letters and digits, one
  ``split_tokens`` token), so a code word maps to a term exactly. Namespaces stay in the code: ``quadtree.Index`` is Quadtree and Index.
- SKOS S13: a term's preferred, alternative and hidden labels are pairwise disjoint.
- SKOS S14, extended to the scheme: one word names one term. This is also Deissenboeck and
  Pizka's naming consistency (one name, one concept), stated where the names are agreed.
- ``broader`` and ``related`` name existing terms by their preferred label; ``broader`` has no
  cycle; and SKOS S27: two terms are not both related and linked by a chain of ``broader``.
"""
from __future__ import annotations

import re

from ..lexicon.tokenize import split_tokens
from .model import Scheme, Term


#: a word as it can appear inside an identifier
_WORD = re.compile(r"[A-Za-z][A-Za-z0-9]*")


def problems(scheme: Scheme) -> tuple[str, ...]:
    """Every integrity problem in ``scheme``, in term order; empty when it is consistent."""
    found: list[str] = []
    owner: dict[str, str] = {}
    preferred = {t.pref_label.lower(): t for t in scheme.terms}
    for term in scheme.terms:
        found += _labels(term, owner)
        found += [f"{term.pref_label}: {kind} names no term '{label}'"
                  for kind, labels in (("broader", term.broader), ("related", term.related))
                  for label in labels if label.lower() not in preferred]
    ancestors = {t.pref_label.lower(): _ancestors(t, preferred) for t in scheme.terms}
    for term in scheme.terms:
        own = term.pref_label.lower()
        if own in ancestors[own]:
            found.append(f"{term.pref_label}: broader leads back to itself")
        for label in term.related:
            other = label.lower()
            if other in ancestors[own] or own in ancestors.get(other, set()):
                found.append(f"{term.pref_label}: related to {label}, which is also on its broader chain")
    return tuple(found)


def _labels(term: Term, owner: dict[str, str]) -> list[str]:
    found = []
    seen: set[str] = set()
    for label in term.labels():
        word = label.lower()
        if not _WORD.fullmatch(label) or len(split_tokens(label)) != 1:
            found.append(f"{term.pref_label}: label '{label}' is not a single word")
        if word in seen:
            found.append(f"{term.pref_label}: label '{label}' appears twice in one term")
        elif word in owner and owner[word] != term.pref_label:
            found.append(f"{term.pref_label}: label '{label}' already names {owner[word]}")
        seen.add(word)
        owner.setdefault(word, term.pref_label)
    return found


def _ancestors(term: Term, preferred: dict[str, Term]) -> set[str]:
    """Every term reachable through ``broader``, by lower-cased preferred label."""
    reached: set[str] = set()
    stack = [b.lower() for b in term.broader]
    while stack:
        label = stack.pop()
        if label in reached:
            continue
        reached.add(label)
        if label in preferred:
            stack.extend(b.lower() for b in preferred[label].broader)
    return reached
