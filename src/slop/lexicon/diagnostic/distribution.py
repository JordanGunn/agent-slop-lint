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
from typing import Any, Iterable


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
