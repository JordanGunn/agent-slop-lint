"""Distribution primitives — histograms + summary statistics.

The values-receiver cluster from the legacy ``diagnostics.py``:
histogram binning (equal-width and power-of-2 log) and
distribution summaries with n / mean / median / p90 / max + histogram.

JSON-serialisable output for observation documents that need
reproducible distribution shape data.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping


@dataclass(frozen=True)
class HistogramBin:
    """One bin in a histogram: ``[lo, hi)`` with ``count`` values inside."""

    lo: float
    hi: float
    count: int

    def as_dict(self) -> dict[str, Any]:
        return {"lo": self.lo, "hi": self.hi, "count": self.count}


def histogram_buckets(
    values: Iterable[float], *, bins: int = 10,
) -> list[HistogramBin]:
    """Equal-width binning over ``[min(values), max(values)]``.

    Returns ``bins`` left-closed right-open intervals; the final bin is
    closed on both sides so ``max(values)`` lands inside it. Empty input
    yields an empty list. A degenerate input (all-equal values) returns
    a single bin around the value.
    """
    vals = list(values)
    if not vals:
        return []
    lo, hi = min(vals), max(vals)
    if lo == hi:
        return [HistogramBin(lo=lo, hi=lo, count=len(vals))]
    width = (hi - lo) / bins
    edges = [lo + i * width for i in range(bins + 1)]
    edges[-1] = hi
    counts = [0] * bins
    for v in vals:
        idx = int((v - lo) / width)
        if idx >= bins:
            idx = bins - 1
        counts[idx] += 1
    return [
        HistogramBin(lo=edges[i], hi=edges[i + 1], count=counts[i])
        for i in range(bins)
    ]


def log_buckets(
    values: Iterable[int], *, max_bin_exp: int = 10,
) -> list[HistogramBin]:
    """Power-of-2 binning for skewed integer distributions.

    Bins are ``[1,2), [2,4), [4,8), ...`` up to ``2^max_bin_exp``;
    values >= ``2^max_bin_exp`` go in the final open-ended bin
    (its ``hi`` is reported as ``inf``).
    """
    vals = [v for v in values if v >= 1]
    if not vals:
        return []
    counts = [0] * (max_bin_exp + 1)
    for v in vals:
        if v >= 2 ** max_bin_exp:
            counts[-1] += 1
        else:
            counts[int(math.log2(v))] += 1
    bins: list[HistogramBin] = []
    for i in range(max_bin_exp):
        if counts[i]:
            bins.append(HistogramBin(
                lo=float(2 ** i), hi=float(2 ** (i + 1)), count=counts[i],
            ))
    if counts[-1]:
        bins.append(HistogramBin(
            lo=float(2 ** max_bin_exp), hi=float("inf"), count=counts[-1],
        ))
    return bins


@dataclass(frozen=True)
class Summary:
    """Numeric distribution summary with histogram.

    Carried in the JSON output so an analysis pass can answer "is this
    distribution skewed?" / "what's the long tail?" without re-running
    the suite.
    """

    name: str
    n: int
    mean: float
    median: float
    p90: float
    max: float
    histogram: list[HistogramBin] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "n": self.n,
            "mean": round(self.mean, 4),
            "median": round(self.median, 4),
            "p90": round(self.p90, 4),
            "max": round(self.max, 4),
            "histogram": [b.as_dict() for b in self.histogram],
        }


def summary(
    values: Iterable[float], *, name: str, log_bins: bool = False,
    max_bin_exp: int = 10, equal_width_bins: int = 10,
) -> Summary:
    """Compute summary statistics + histogram for a numeric distribution."""
    vals = sorted(values)
    if not vals:
        return Summary(name=name, n=0, mean=0.0, median=0.0,
                       p90=0.0, max=0.0, histogram=[])
    n = len(vals)
    mean = sum(vals) / n
    median = vals[n // 2] if n % 2 == 1 else (vals[n // 2 - 1] + vals[n // 2]) / 2
    p90_idx = max(0, int(0.9 * (n - 1)))
    p90 = vals[p90_idx]
    hist = (
        log_buckets((int(v) for v in vals), max_bin_exp=max_bin_exp)
        if log_bins
        else histogram_buckets(vals, bins=equal_width_bins)
    )
    return Summary(
        name=name, n=n, mean=mean, median=median, p90=p90,
        max=vals[-1], histogram=hist,
    )


# ---------------------------------------------------------------------------
# Token distribution — the identifier vocabulary as a Zipfian object
# ---------------------------------------------------------------------------

# Population norms measured 2026-05-29 across engineered Python corpora (see
# project memory `lexical-distribution-invariance`). Identifier vocabularies
# cluster tightly here REGARDLESS of size or discipline — they're closer to a
# Zipf/Heaps constant than a quality dial. They anchor the natural-language
# narration as "typical", not as a pass/fail threshold; emit no verdict.
ZIPF_ALPHA_NORM = 0.90
ZIPF_R2_NORM = 0.93
HAPAX_RATIO_NORM = 0.49


def _zipf_fit(counts: list[int]) -> tuple[float, float]:
    """OLS fit of log(freq) ~ log(rank); return (alpha, r2).

    ``alpha`` is the negated slope (Zipf exponent); ``r2`` the fit
    quality. Needs >= 2 distinct rank points — returns ``(0.0, 0.0)``
    for a degenerate vocabulary.
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
    """The identifier token space as a measured distribution.

    The hapax ratio is one bucket (``spectrum["1"]``) of this richer
    object; ``narrate()`` turns the whole thing into the prose an agent
    investigates. JSON-serialisable via ``as_dict``.
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

        Deliberately prose, not a stats dump: an agent reads this and
        decides whether to look closer. Compares against population norms
        without asserting a defect.
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


@dataclass(frozen=True)
class ConceptOwnership:
    """Cross-view ownership of one concept token across packages.

    The across-namespace axis: where a token's uses concentrate, and
    whether a token that *names* a package actually lives there. Needs the
    structural import graph (passed in) to gate owner-displacement — a
    concept whose lexical owner merely *imports* its eponymous package is
    a legitimate consumer (layering), not an escape.
    """

    token: str
    total: int
    owner: str                       # package with the most uses
    concentration: float             # owner's share of the token's uses
    package_count: int               # distinct packages the token touches
    names_package: bool              # the token is itself a package name
    displaced: bool                  # names a package but is owned elsewhere
    owner_imports_eponymous: bool    # the gate: owner imports the eponymous package

    def verdict(self) -> str:
        """Classify: the only actionable class is ``displaced_unexplained``."""
        if self.displaced and not self.owner_imports_eponymous:
            return "displaced_unexplained"
        if self.displaced:
            return "displaced_explained"      # layering — suppressed
        if self.package_count >= 4 and self.concentration < 0.5:
            return "cross_cutting"            # generic plumbing, no owner
        return "cohesive"

    def as_dict(self) -> dict[str, Any]:
        return {
            "token": self.token,
            "total": self.total,
            "owner": self.owner,
            "concentration": round(self.concentration, 3),
            "package_count": self.package_count,
            "names_package": self.names_package,
            "displaced": self.displaced,
            "owner_imports_eponymous": self.owner_imports_eponymous,
            "verdict": self.verdict(),
        }


def token_distribution(
    freq: Mapping[str, int], *, top: int = 15,
) -> TokenDistribution:
    """Characterize a token-frequency mapping as a distribution.

    ``freq`` is token -> occurrence count (e.g. ``Lexicon.frequencies()``).
    Returns the full distribution object; empty input yields a zeroed one.
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
