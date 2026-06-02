"""Distribution — the identifier token-space as a measured Zipfian object.

An identifier vocabulary is a frequency distribution, and engineered code sits at a
remarkably tight near-invariant: a Zipf exponent around 0.9 with R² around 0.93, and
roughly half the vocabulary appearing exactly once. Those are *population norms*, not
quality dials — so this module measures the shape and narrates it against the norm,
and never emits a verdict. That claim-free posture is why the ``vocabulary`` rule can
surface this object as an Observation: a measurement an agent investigates, not a
defect the linter asserts.

This is lexicography a corpus linguist would recognise (Zipf/Heaps, hapax legomena),
so it lives in the kernel. The norm constants and the prose comparison bands are
descriptive, carrying no severity and no pass/fail threshold.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Mapping

# Population norms measured across engineered Python corpora (2026-05-29; see project
# memory `lexical-distribution-invariance`). Identifier vocabularies cluster tightly
# here regardless of size or discipline — closer to a Zipf/Heaps constant than a
# quality dial. They anchor the narration as "typical", never as pass/fail.
ZIPF_ALPHA_NORM = 0.90
ZIPF_R2_NORM = 0.93
HAPAX_RATIO_NORM = 0.49


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

    The hapax ratio is one bucket (``spectrum["1"]``) of this richer object;
    ``narrate()`` turns the whole thing into the prose an agent investigates.
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
            "norms": {
                "zipf_alpha": ZIPF_ALPHA_NORM,
                "zipf_r2": ZIPF_R2_NORM,
                "hapax_ratio": HAPAX_RATIO_NORM,
            },
        }

    def narrate(self) -> str:
        """Natural-language transform of the distribution.

        Deliberately prose, not a stats dump: an agent reads this and decides
        whether to look closer. Compares against population norms without asserting
        a defect — an investigative nudge, never a verdict.
        """
        if self.distinct == 0:
            return "No identifier vocabulary to analyze (empty corpus)."

        parts: list[str] = [
            f"Identifier vocabulary: {self.distinct} distinct tokens across "
            f"{self.n} uses."
        ]

        # Reuse gradient (Zipf fit) vs the typical ~0.9 / R^2~0.93.
        if self.zipf_r2 >= 0.85 and abs(self.zipf_alpha - ZIPF_ALPHA_NORM) <= 0.15:
            parts.append(
                f"Reuse follows a healthy Zipfian gradient "
                f"(α={self.zipf_alpha:.2f}, R²={self.zipf_r2:.2f}), "
                f"typical of engineered code."
            )
        elif self.zipf_r2 < 0.80:
            parts.append(
                f"Reuse fits Zipf poorly (R²={self.zipf_r2:.2f} vs the "
                f"~{ZIPF_R2_NORM} norm) — a lumpy vocabulary without a "
                f"clean reuse gradient; worth a look at how concepts are named."
            )
        elif self.zipf_alpha < ZIPF_ALPHA_NORM - 0.15:
            parts.append(
                f"The reuse gradient is unusually flat (α={self.zipf_alpha:.2f} "
                f"vs ~{ZIPF_ALPHA_NORM}): few concepts are reused while many "
                f"appear once — possible vocabulary fragmentation."
            )
        else:
            parts.append(
                f"Reuse gradient α={self.zipf_alpha:.2f}, "
                f"R²={self.zipf_r2:.2f} (norm ~{ZIPF_ALPHA_NORM})."
            )

        # Hapax floor.
        pct = round(self.hapax_ratio * 100)
        if self.hapax_ratio > HAPAX_RATIO_NORM + 0.15:
            parts.append(
                f"{pct}% of tokens appear exactly once — above the ~"
                f"{round(HAPAX_RATIO_NORM * 100)}% long-tail floor, a fatter "
                f"one-off tail than usual."
            )
        else:
            parts.append(
                f"{pct}% of tokens appear exactly once (the expected "
                f"long-tail floor)."
            )

        # Dominant concept.
        if self.top:
            lead, lead_n = self.top[0]
            if len(self.top) > 1 and lead_n >= 2 * self.top[1][1]:
                parts.append(
                    f"The vocabulary centers hard on `{lead}` ({lead_n} uses), "
                    f"far ahead of `{self.top[1][0]}` ({self.top[1][1]}) — "
                    f"this is the codebase's dominant concept."
                )
            else:
                lead_str = ", ".join(f"`{t}` ({c})" for t, c in self.top[:3])
                parts.append(f"Most-used concepts: {lead_str}.")

        return " ".join(parts)


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
