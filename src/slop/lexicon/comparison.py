"""Comparison — relational lexicostatistics between two token-spaces.

Single-lexicon measurement (Zipf/hapax) lives in ``distribution``; this module adds
the *pairwise* primitive the kernel previously lacked: how alike are two
vocabularies? A corpus linguist would recognise every member here — set overlap
(Jaccard), directional containment, frequency cosine, and Jensen-Shannon divergence
between the two distributions. No slop-invented metric and no verdict: the rule layer
above decides what a given similarity *means* (a scope whose vocabulary fits a sibling
package better than its own is a relocation candidate; one that barely overlaps its
container is a foreign body) — this layer only measures the likeness.

All functions take token -> count mappings (``Lexicon.frequencies()``) and return a
value in a documented range. They are symmetric unless named otherwise
(``containment`` is directional). Frequency is ignored by ``jaccard``/``containment``
(presence only) and used by ``cosine``/``js_*`` (distribution shape).
"""
from __future__ import annotations

import math
from typing import Mapping

Freq = Mapping[str, int]


def jaccard(a: Freq, b: Freq) -> float:
    """Set overlap of distinct tokens: ``|A∩B| / |A∪B|``. 0 = disjoint vocabularies,
    1 = identical token sets. Presence/absence only — frequency is ignored. Two empty
    inputs yield 0 (no shared vocabulary to speak of)."""
    sa, sb = set(a), set(b)
    union = sa | sb
    return len(sa & sb) / len(union) if union else 0.0


def containment(a: Freq, b: Freq) -> float:
    """Directional overlap: ``|A∩B| / |A|`` — the fraction of A's vocabulary that
    also appears in B. ``containment(child, container)`` reads as "how much of the
    child's vocabulary the container shares". 0 if A is empty."""
    sa = set(a)
    if not sa:
        return 0.0
    return len(sa & set(b)) / len(sa)


def cosine(a: Freq, b: Freq) -> float:
    """Frequency-weighted cosine over the shared vocabulary: 0 = orthogonal, 1 =
    identical usage proportions. Unlike Jaccard, a token used heavily in both spaces
    counts for more than a token mentioned once in each. 0 if either side is empty."""
    keys = set(a) | set(b)
    dot = sum(a.get(k, 0) * b.get(k, 0) for k in keys)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def js_divergence(a: Freq, b: Freq) -> float:
    """Jensen-Shannon divergence (base 2) between the two token *distributions* — a
    smoothed, symmetric, bounded distance in ``[0, 1]``. 0 = identical distributions,
    1 = maximally divergent (disjoint vocabularies). Frequencies are normalised to
    probabilities first; an empty side is treated as maximally divergent (1.0)."""
    ta = sum(a.values())
    tb = sum(b.values())
    if ta == 0 or tb == 0:
        return 1.0
    pa = {k: v / ta for k, v in a.items()}
    pb = {k: v / tb for k, v in b.items()}
    keys = set(pa) | set(pb)
    mix = {k: 0.5 * (pa.get(k, 0.0) + pb.get(k, 0.0)) for k in keys}

    def _kl(p: dict[str, float]) -> float:
        total = 0.0
        for k, pk in p.items():
            if pk > 0.0:
                total += pk * math.log2(pk / mix[k])
        return total

    return 0.5 * _kl(pa) + 0.5 * _kl(pb)


def js_similarity(a: Freq, b: Freq) -> float:
    """``1 - js_divergence``: a ``[0, 1]`` similarity over the token distributions
    (1 = identical, 0 = maximally divergent). The distribution-aware twin of
    ``jaccard`` — penalises a different *balance* of shared tokens, not just a
    different token set."""
    return 1.0 - js_divergence(a, b)
