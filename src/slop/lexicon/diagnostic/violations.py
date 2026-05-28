"""Violation accounting — multi-scope counts + rule × cell cross-tab.

The lexicon-receiver cluster from the legacy ``diagnostics.py``:
runs rules against a lexicon view and either buckets findings by
scope (file / package / root / callable) or joins them with the
three-planes (A=packets, B=frequency-head, C=spread) diagnostic cell.

Both surfaces support the same use case — answering "where do
violations land?" — at different granularities.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from slop.linter.rule import Rule
from slop.config import Config
from slop.lexicon.view import Lexicon
from slop.linter.slop import Slop
from slop.linter.types import RuleDefinition


# ---------------------------------------------------------------------------
# Multi-scope violation counting
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


def count_by_scope(
    lexicon: Lexicon,
    rule_defs: Iterable[RuleDefinition],
    *,
    rule_configs: Mapping[str, Rule],
    slop_config: Config,
    scope: str = "file",
    root: Path | None = None,
) -> list[ScopedViolationCount]:
    """Run each rule once on the whole lexicon; bucket violations by ``scope``.

    Each rule definition is executed against the given lexicon view with
    its configured ``Rule`` (or a default-enabled stand-in if the
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
            Rule(enabled=True, severity=rule_def.default_severity, params={}),
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
# Rule × cell cross-tab
# ---------------------------------------------------------------------------
#
# Joins Layer 1 (rule violations) with Layer 2 (diagnostic cell membership)
# for each violation's symbol. The (rule, cell) matrix is the empirical
# basis for corrective-action mapping: which rule + cell combinations
# indicate which kind of refactor (missing module / missing class / etc.)?

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


def with_cells(
    lexicon: Lexicon,
    rule_defs: Iterable[RuleDefinition],
    *,
    rule_configs: Mapping[str, Rule],
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
            Rule(enabled=True, severity=rule_def.default_severity, params={}),
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


def tabulate_cells(
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


def format_cells(
    records: Iterable[ViolationCell],
    rule_defs: Iterable[RuleDefinition],
) -> str:
    """Render the rule×cell matrix as a fixed-width text table.

    Rows are rules (in registry order); columns are the 8 cells in
    ``_CELL_PRIORITY`` order. Cell value is the violation count.
    Zero counts render as ``.`` to keep the table scannable.
    """
    grid = tabulate_cells(records)
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
