"""Cross-rule overlap analysis — rank targets where concerns converge.

The rule-centric report answers "what does each rule find". This answers
the question that actually drives action: "where do multiple INDEPENDENT
concerns converge" — the fix-first signal a flat per-rule listing hides.

A concern *family* is the rule's namespace: ``complexity.*`` /
``lexical.*`` / ``inheritance.*`` each collapse to one family because their
metrics are correlated (a complex function trips all of cyclomatic /
cognitive / NPath trivially — that's one concern, not three). Every
standalone rule is its own family. A target tripping many *families* is
more urgent than one tripping many correlated metrics of a single family,
and that's what the ranking surfaces.

Observations (claim-free instrumentation) are excluded — only verdicts
count toward overlap.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from slop.linter.types import RuleResult


def family_of(rule_name: str) -> str:
    """Concern family for a rule: its namespace, else its own name.

    ``complexity.cyclomatic`` → ``complexity``; ``lexical.stutter`` →
    ``lexical``; ``coupling`` → ``coupling``.
    """
    return rule_name.split(".", 1)[0]


@dataclass
class SymbolOverlap:
    """One symbol (function/class) and the families that fire on it."""

    symbol: str
    scope: str | None
    families: list[str]

    def as_dict(self) -> dict:
        return {"symbol": self.symbol, "scope": self.scope, "families": self.families}


@dataclass
class TargetOverlap:
    """One file ranked by how many independent concern families it trips."""

    file: str
    families: list[str]
    finding_count: int
    symbols: list[SymbolOverlap] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "file": self.file,
            "families": self.families,
            "concern_count": len(self.families),
            "finding_count": self.finding_count,
            "symbols": [s.as_dict() for s in self.symbols],
        }


def compute_overlap(
    rule_results: "dict[str, RuleResult]",
    *,
    top: int = 8,
    min_families: int = 2,
) -> list[TargetOverlap]:
    """Rank files by distinct concern families, descending.

    Only files tripping at least ``min_families`` independent families are
    returned (a single-family file is not "overlap"); capped at ``top``.
    Each target carries its co-firing symbols (those tripping ≥ 2 families).
    """
    file_families: dict[str, set[str]] = {}
    file_count: dict[str, int] = {}
    symbol_families: dict[tuple[str, str | None, str], set[str]] = {}

    for name, rr in rule_results.items():
        fam = family_of(name)
        for v in rr.violations:
            file_families.setdefault(v.file, set()).add(fam)
            file_count[v.file] = file_count.get(v.file, 0) + 1
            if v.symbol and v.scope in ("function", "class"):
                symbol_families.setdefault((v.file, v.scope, v.symbol), set()).add(fam)

    targets: list[TargetOverlap] = []
    for file, families in file_families.items():
        if len(families) < min_families:
            continue
        symbols = [
            SymbolOverlap(symbol=sym, scope=scope, families=sorted(fams))
            for (sym_file, scope, sym), fams in symbol_families.items()
            if sym_file == file and len(fams) >= 2
        ]
        symbols.sort(key=lambda s: (-len(s.families), s.symbol))
        targets.append(TargetOverlap(
            file=file,
            families=sorted(families),
            finding_count=file_count[file],
            symbols=symbols,
        ))

    targets.sort(key=lambda t: (-len(t.families), -t.finding_count, t.file))
    return targets[:top]
