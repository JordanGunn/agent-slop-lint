"""Distribution: the identifier words as a measured Zipfian frequency distribution.

Its Zipf exponent and fit, the share of words used once (hapax legomena), and how
concentrated its head is. It measures the shape and checks nothing against it.

It reports no population norm beside the measurement: no norm traceable to a reproducible
measurement exists, and over declared names slop and laszy both measure near Zipf α 1.0,
R² 0.94 and a hapax ratio of 0.36, which is no population either.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Mapping

def _zipf_fit(counts: list[int]) -> tuple[float, float]:
    """OLS fit of ``log(freq) ~ log(rank)``; return ``(alpha, r2)``.

    ``alpha`` is the negated slope (the Zipf exponent); ``r2`` the fit quality. Needs
    >= 2 distinct rank points — returns ``(0.0, 0.0)`` for a degenerate vocabulary.
    """
    if len(counts) < 2:
        return 0.0, 0.0
    xs = [math.log(r) for r in range(1, len(counts) + 1)]
    ys = [math.log(c) for c in counts]
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0:
        return 0.0, 0.0
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    slope = sxy / sxx
    ss_tot = sum((y - my) ** 2 for y in ys)
    ss_res = sum((y - (my + slope * (x - mx))) ** 2 for x, y in zip(xs, ys))
    r2 = 1 - ss_res / ss_tot if ss_tot else 0.0
    return -slope, r2


@dataclass(frozen=True)
class TokenDistribution:
    """The identifier token-space as a measured distribution.

    The hapax ratio is one bucket (``spectrum["1"]``) of this richer object.
    JSON-serialisable via ``as_dict``.
    """

    n: int                          # total token occurrences
    distinct: int                   # vocabulary size (distinct tokens)
    hapax: int                      # tokens appearing exactly once
    hapax_ratio: float
    dis: int                        # tokens appearing exactly twice
    dis_ratio: float
    zipf_alpha: float
    zipf_r2: float
    head_concentration: float       # share of occurrences in the top-10 tokens
    spectrum: dict[str, int]        # freq-of-freq: "1".."10", ">10"
    top: list[tuple[str, int]]      # most common tokens, descending

    def as_dict(self) -> dict[str, Any]:
        return {
            "n": self.n,
            "distinct": self.distinct,
            "hapax": self.hapax,
            "hapax_ratio": round(self.hapax_ratio, 4),
            "dis": self.dis,
            "dis_ratio": round(self.dis_ratio, 4),
            "zipf_alpha": round(self.zipf_alpha, 4),
            "zipf_r2": round(self.zipf_r2, 4),
            "head_concentration": round(self.head_concentration, 4),
            "spectrum": self.spectrum,
            "top": [{"token": t, "count": c} for t, c in self.top],
        }


def token_distribution(freq: Mapping[str, int], *, top: int = 15) -> TokenDistribution:
    """Characterise a token-frequency mapping as a distribution.

    ``freq`` is token -> occurrence count (e.g. ``Lexicon.frequencies()``). Returns
    the full distribution object; empty input yields a zeroed one.
    """
    items = sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))
    counts = [c for _, c in items]
    n = sum(counts)
    distinct = len(counts)
    if distinct == 0:
        return TokenDistribution(
            n=0, distinct=0, hapax=0, hapax_ratio=0.0, dis=0, dis_ratio=0.0,
            zipf_alpha=0.0, zipf_r2=0.0, head_concentration=0.0,
            spectrum={}, top=[],
        )

    spec: dict[str, int] = {str(k): 0 for k in range(1, 11)}
    spec[">10"] = 0
    for c in counts:
        spec[str(c) if c <= 10 else ">10"] += 1

    hapax = spec["1"]
    dis = spec["2"]
    alpha, r2 = _zipf_fit(counts)
    head10 = sum(counts[:10]) / n if n else 0.0

    return TokenDistribution(
        n=n,
        distinct=distinct,
        hapax=hapax,
        hapax_ratio=hapax / distinct,
        dis=dis,
        dis_ratio=dis / distinct,
        zipf_alpha=alpha,
        zipf_r2=r2,
        head_concentration=head10,
        spectrum=spec,
        top=items[:top],
    )
