"""Research diagnostic suite — multi-scope measurement, histograms, JSON emission, rule×cell cross-tab.

The instrumentation layer that lets observation documents produce
reproducible, queryable structured data. Three composable surfaces:

- ``count_violations_by_scope`` — run lexical rules against the whole
  view once, then bucket findings into scope (file / package / root /
  callable) for per-scope violation counts. The default validation
  harness for "does this rule fire more in one scope than another?".

- ``histogram_buckets`` / ``log_buckets`` — distribution shape over a
  list of numeric values. Used for sprawl token-spread distributions,
  packet-size distributions, association-score distributions, etc.

- ``distribution_summary`` / ``emit_diagnostic_report`` — JSON-serialisable
  shapes for observation documents. Each summary carries n / mean /
  median / p90 / max + histogram so a later analysis pass can derive
  conclusions without re-parsing the corpus.

The format is intentionally observation-internal and versionless — per
R5 in the IRIS contract, locking a schema before consumers are known
would over-commit. Treat the dicts as adhoc until the consumer set
stabilises.

See ``docs/research/observations/`` for the consumers.
"""
from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

from slop.linter.rule_config import RuleConfig
from slop.config import Config
from slop.lexicon.view import Lexicon
from slop.linter.slop import Slop
from slop.linter.types import RuleDefinition


# ---------------------------------------------------------------------------
# Multi-scope violation measurement (D8)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ScopedViolationCount:
    """One ``{rule, scope-axis, scope-key} -> count`` record."""

    rule: str
    scope: str    # "file" | "package" | "root" | "callable"
    key: str      # path / qualname / "<root>"
    count: int


def _scope_key_for(violation: Slop, scope: str, root: Path | None) -> str:
    """Map a violation to its scope key for the chosen axis."""
    file_path = Path(violation.file) if violation.file else None
    if scope == "root":
        return "<root>"
    if scope == "file":
        if file_path is None:
            return "<unknown>"
        if root is not None:
            try:
                return str(file_path.relative_to(root))
            except ValueError:
                pass
        return str(file_path)
    if scope == "package":
        if file_path is None:
            return "<unknown>"
        pkg = file_path.parent
        if root is not None:
            try:
                return str(pkg.relative_to(root))
            except ValueError:
                pass
        return str(pkg)
    if scope == "callable":
        sym = violation.symbol or "<anonymous>"
        if file_path is None:
            return sym
        rel = file_path
        if root is not None:
            try:
                rel = file_path.relative_to(root)
            except ValueError:
                pass
        return f"{rel}::{sym}"
    raise ValueError(f"unknown scope {scope!r}; expected file|package|root|callable")


def count_violations_by_scope(
    lexicon: Lexicon,
    rule_defs: Iterable[RuleDefinition],
    *,
    rule_configs: Mapping[str, RuleConfig],
    slop_config: Config,
    scope: str = "file",
    root: Path | None = None,
) -> list[ScopedViolationCount]:
    """Run each rule once on the whole lexicon; bucket violations by ``scope``.

    Each rule definition is executed against the given lexicon view with
    its configured ``RuleConfig`` (or a default-enabled stand-in if the
    rule is missing from ``rule_configs``). Returned counts span the
    cartesian product of (rules that fired) × (scope keys that received
    findings); empty buckets are omitted.

    The ``scope`` axis is one of ``file`` / ``package`` / ``root`` /
    ``callable``. ``root`` collapses everything into a single bucket
    (useful for whole-corpus totals); the others split by violation
    location.
    """
    out: list[ScopedViolationCount] = []
    for rule_def in rule_defs:
        rc = rule_configs.get(
            rule_def.name,
            RuleConfig(enabled=True, severity=rule_def.default_severity, params={}),
        )
        try:
            result = rule_def.run(lexicon, rc, slop_config)
        except Exception:
            continue
        if not result.violations:
            continue
        bucket: dict[str, int] = defaultdict(int)
        for v in result.violations:
            bucket[_scope_key_for(v, scope, root)] += 1
        for key, n in sorted(bucket.items()):
            out.append(ScopedViolationCount(
                rule=rule_def.name, scope=scope, key=key, count=n,
            ))
    return out


# ---------------------------------------------------------------------------
# Histograms (D9)
# ---------------------------------------------------------------------------


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
    edges[-1] = hi  # exact-equal close to dodge float-creep
    counts = [0] * bins
    for v in vals:
        # left-closed right-open; the last bin includes hi
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


# ---------------------------------------------------------------------------
# Distribution summaries + JSON emission (D10)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DistributionSummary:
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


def distribution_summary(
    values: Iterable[float], *, name: str, log_bins: bool = False,
    max_bin_exp: int = 10, equal_width_bins: int = 10,
) -> DistributionSummary:
    """Compute summary statistics + histogram for a numeric distribution."""
    vals = sorted(values)
    if not vals:
        return DistributionSummary(name=name, n=0, mean=0.0, median=0.0,
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
    return DistributionSummary(
        name=name, n=n, mean=mean, median=median, p90=p90,
        max=vals[-1], histogram=hist,
    )


def emit_diagnostic_report(
    lexicon: Lexicon,
    *,
    rule_defs: Iterable[RuleDefinition] | None = None,
    rule_configs: Mapping[str, RuleConfig] | None = None,
    slop_config: Config | None = None,
    root: Path | None = None,
    class_vocabularies: Mapping[str, set[str]] | None = None,
    exclude_tokens: frozenset[str] = frozenset(),
    packet_min_bags: int = 5,
    packet_min_association: float = 0.7,
) -> dict[str, Any]:
    """Compose the full diagnostic dict for one corpus.

    Sections:
      - ``corpus``: file counts, callable counts
      - ``distributions``: token-frequency, sprawl token-spread, packet sizes
      - ``packets``: callable-scope + file-scope packets, pathological vs
        conventional (when class_vocabularies is supplied)
      - ``violations_by_scope``: per-scope violation counts when
        rule_defs + rule_configs + slop_config are supplied

    The dict is JSON-serialisable. Intentionally schema-versionless;
    consumers should be defensive.
    """
    from slop.lexicon.filters import split_packets_by_class_ownership

    files = list(lexicon.files())
    callables = list(lexicon.callables())

    freq = lexicon.frequencies(exclude=exclude_tokens)
    locs = lexicon.token_locations(exclude=exclude_tokens)

    dist_freq = distribution_summary(
        list(freq.values()), name="token_occurrence_count", log_bins=True,
    )
    dist_sprawl = distribution_summary(
        [len(files) for files in locs.values()],
        name="token_file_spread", log_bins=True,
    )

    callable_packets = lexicon.packets(
        scope="callable", min_bags=packet_min_bags,
        min_association=packet_min_association, exclude=exclude_tokens,
    )
    file_packets = lexicon.packets(
        scope="file", min_bags=packet_min_bags,
        min_association=packet_min_association, exclude=exclude_tokens,
    )

    dist_packet_callable = distribution_summary(
        [len(p) for p in callable_packets],
        name="packet_size_callable_scope",
    )
    dist_packet_file = distribution_summary(
        [len(p) for p in file_packets],
        name="packet_size_file_scope",
    )

    packets_section: dict[str, Any] = {
        "thresholds": {
            "min_bags": packet_min_bags,
            "min_association": packet_min_association,
        },
        "callable_scope": {
            "total": len(callable_packets),
            "packets": [sorted(p) for p in callable_packets],
        },
        "file_scope": {
            "total": len(file_packets),
            "packets": [sorted(p) for p in file_packets],
        },
    }

    if class_vocabularies is not None:
        from slop.lexicon.actions import map_packets_to_actions

        path_c, conv_c = split_packets_by_class_ownership(
            callable_packets, dict(class_vocabularies),
        )
        path_f, conv_f = split_packets_by_class_ownership(
            file_packets, dict(class_vocabularies),
        )
        actions_c = map_packets_to_actions(path_c, lexicon, scope="callable")
        actions_f = map_packets_to_actions(path_f, lexicon, scope="file")
        packets_section["callable_scope"]["pathological"] = [
            a.as_dict() for a in actions_c
        ]
        packets_section["callable_scope"]["conventional"] = [
            {"packet": sorted(p), "class": cls} for p, cls in conv_c
        ]
        packets_section["file_scope"]["pathological"] = [
            a.as_dict() for a in actions_f
        ]
        packets_section["file_scope"]["conventional"] = [
            {"packet": sorted(p), "class": cls} for p, cls in conv_f
        ]

    report: dict[str, Any] = {
        "corpus": {
            "files": len(files),
            "callables": len(callables),
            "distinct_tokens": len(freq),
        },
        "thresholds": {
            "exclude_tokens": sorted(exclude_tokens),
        },
        "distributions": {
            "token_occurrence_count": dist_freq.as_dict(),
            "token_file_spread": dist_sprawl.as_dict(),
            "packet_size_callable_scope": dist_packet_callable.as_dict(),
            "packet_size_file_scope": dist_packet_file.as_dict(),
        },
        "packets": packets_section,
    }

    if rule_defs is not None and rule_configs is not None and slop_config is not None:
        scopes_section: dict[str, list[dict[str, Any]]] = {}
        for axis in ("file", "package", "root", "callable"):
            counts = count_violations_by_scope(
                lexicon, rule_defs,
                rule_configs=rule_configs, slop_config=slop_config,
                scope=axis, root=root,
            )
            scopes_section[axis] = [
                {"rule": c.rule, "key": c.key, "count": c.count} for c in counts
            ]
        report["violations_by_scope"] = scopes_section

    return report


# ---------------------------------------------------------------------------
# Rule × cell cross-tabulation (obs 09)
# ---------------------------------------------------------------------------
#
# Joins Layer 1 (rule violations) with Layer 2 (diagnostic cell membership)
# for each violation's symbol. The (rule, cell) matrix is the empirical
# basis for corrective-action mapping: which rule + cell combinations
# indicate which kind of refactor (missing module / missing class / etc.)?
#
# See docs/research/observations/09-*.md for the consumer and discussion.


# Cell priority for picking a "primary cell" when a symbol's tokens span
# multiple cells. Packet-bearing always wins (those tokens are bonded);
# then frequency-head + spread (concentrated), then spread-only, then
# frequency-only, then "below all thresholds" (tail).
_CELL_PRIORITY: list[str] = [
    "ABC", "AB-", "A-C", "A--",
    "-BC", "-B-", "--C", "---",
]


@dataclass(frozen=True)
class ViolationCell:
    """One violation, classified by its symbol-tokens' lexicon-cell address.

    ``cell`` is one of the 8 codes ``ABC``, ``AB-``, ``A-C``, ``A--``,
    ``-BC``, ``-B-``, ``--C``, ``---`` per the obs-07 three-planes
    matrix. ``primary_token`` is the single token from the symbol that
    drove the cell choice (the highest-priority cell among its tokens).
    """

    rule: str
    cell: str
    primary_token: str
    symbol: str
    file: str
    line: int | None
    tokens: tuple[str, ...]
    severity: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "rule": self.rule, "cell": self.cell,
            "primary_token": self.primary_token,
            "symbol": self.symbol, "file": self.file, "line": self.line,
            "tokens": list(self.tokens), "severity": self.severity,
        }


def _classify_cell(
    token: str,
    *,
    plane_a: set[str], plane_b: set[str], plane_c: set[str],
) -> str:
    """Return the 3-char cell code for one token."""
    return (
        ("A" if token in plane_a else "-")
        + ("B" if token in plane_b else "-")
        + ("C" if token in plane_c else "-")
    )


def _pick_primary_cell(
    tokens: Iterable[str],
    *,
    plane_a: set[str], plane_b: set[str], plane_c: set[str],
) -> tuple[str, str]:
    """Of the token cells in ``tokens``, return ``(best_cell, token)``
    by ``_CELL_PRIORITY`` order. ``"---"`` if no tokens are in any plane.

    Returns ``("---", "")`` for an empty token iterable.
    """
    best_cell = "---"
    best_token = ""
    best_priority = len(_CELL_PRIORITY)
    for t in tokens:
        cell = _classify_cell(t, plane_a=plane_a, plane_b=plane_b, plane_c=plane_c)
        try:
            priority = _CELL_PRIORITY.index(cell)
        except ValueError:
            continue
        if priority < best_priority:
            best_priority = priority
            best_cell = cell
            best_token = t
    return best_cell, best_token


def violations_with_cells(
    lexicon: Lexicon,
    rule_defs: Iterable[RuleDefinition],
    *,
    rule_configs: Mapping[str, RuleConfig],
    slop_config: Config,
    frequency_threshold: int = 8,
    spread_threshold: int = 5,
    packet_min_bags: int = 5,
    packet_min_association: float = 0.7,
    exclude: frozenset[str] = frozenset(),
) -> list[ViolationCell]:
    """Run each rule once; tag every violation with its symbol-tokens' cell.

    For each violation, the symbol is snake/Camel-split into tokens. Each
    token is looked up in the three planes (A=packets, B=frequency head,
    C=spread). The violation's primary cell is the highest-priority cell
    spanned by any of its tokens (see ``_CELL_PRIORITY``).

    A violation whose symbol contains no token in any plane gets cell
    ``---`` — meaning the cited token is below every threshold (the
    long tail), which itself is an interesting signal.
    """
    plane_a: set[str] = set()
    for p in lexicon.packets(
        scope="callable", min_bags=packet_min_bags,
        min_association=packet_min_association, exclude=exclude,
    ):
        plane_a |= p
    plane_b = {t for t, _ in lexicon.frequency_head(
        threshold=frequency_threshold, exclude=exclude,
    )}
    plane_c = {t for t, _ in lexicon.spread_dominant(
        min_spread=spread_threshold, exclude=exclude,
    )}

    out: list[ViolationCell] = []
    for rule_def in rule_defs:
        rc = rule_configs.get(
            rule_def.name,
            RuleConfig(enabled=True, severity=rule_def.default_severity, params={}),
        )
        try:
            result = rule_def.run(lexicon, rc, slop_config)
        except Exception:
            continue
        for v in result.violations:
            symbol = v.symbol or ""
            tokens = tuple(Lexicon.split_tokens(symbol))
            tokens_lower = tuple(t.lower() for t in tokens if t.lower() not in exclude)
            cell, primary = _pick_primary_cell(
                tokens_lower,
                plane_a=plane_a, plane_b=plane_b, plane_c=plane_c,
            )
            out.append(ViolationCell(
                rule=v.rule, cell=cell, primary_token=primary,
                symbol=symbol, file=v.file or "", line=v.line,
                tokens=tokens_lower, severity=v.severity,
            ))
    return out


def tabulate_rule_cell_matrix(
    records: Iterable[ViolationCell],
) -> dict[tuple[str, str], list[ViolationCell]]:
    """Group violations by ``(rule, cell)``. Each bucket retains the
    full ``ViolationCell`` records so callers can inspect exemplars.

    Keys are ``(rule_name, cell_code)``. Cells iterated in
    ``_CELL_PRIORITY`` order; rules iterated in input order.
    """
    out: dict[tuple[str, str], list[ViolationCell]] = defaultdict(list)
    for rec in records:
        out[(rec.rule, rec.cell)].append(rec)
    return dict(out)


def format_rule_cell_matrix(
    records: Iterable[ViolationCell],
    rule_defs: Iterable[RuleDefinition],
) -> str:
    """Render the rule×cell matrix as a fixed-width text table.

    Rows are rules (in registry order); columns are the 8 cells in
    ``_CELL_PRIORITY`` order. Cell value is the violation count.
    Zero counts render as ``.`` to keep the table scannable.
    """
    grid = tabulate_rule_cell_matrix(records)
    rule_names = [r.name for r in rule_defs]
    cells = _CELL_PRIORITY

    rule_col_width = max(len(n) for n in rule_names) + 2
    cell_col_width = 5

    lines: list[str] = []
    header = " " * rule_col_width + "  ".join(f"{c:>{cell_col_width}s}" for c in cells)
    lines.append(header)
    lines.append("─" * len(header))
    for r in rule_names:
        row = f"{r:<{rule_col_width}s}"
        for c in cells:
            n = len(grid.get((r, c), []))
            row += f"  {n:>{cell_col_width}d}" if n else f"  {'.':>{cell_col_width}s}"
        lines.append(row)
    return "\n".join(lines)
