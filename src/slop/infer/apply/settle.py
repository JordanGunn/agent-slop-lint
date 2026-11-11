"""Apply the ledger's rulings to a lint report."""
from __future__ import annotations

from dataclasses import replace
from operator import attrgetter

from ...dispatch import Report
from ..contract import Outcome, Residue
from ..frame.location import project_path
from ..ledger.interface import Ledger
from ..source.finding import FindingSource
from ..source.interface import Analysis


def settle(analysis: Analysis, ledger: Ledger) -> Report:
    """The report with each warning that has a current ruling resolved by it.

    A cleared warning is dropped. A confirmed one becomes a violation, carrying the reason, so
    it fails the run. A deferred warning, a stale ruling and a warning with no ruling stay
    warnings."""
    report = analysis.report
    if next(iter(ledger.rulings()), None) is None:
        return report
    by_place = {(r.rule, r.path, r.subject, r.line, r.column): r for r in FindingSource().residue(analysis)}
    violations, warnings = list(report.violations), []
    for warning in report.warnings:
        item = _residue_of(warning, analysis, by_place)
        ruling = ledger.current(item) if item is not None else None
        if ruling is None or ruling.verdict.outcome is Outcome.DEFER:
            warnings.append(warning)
        elif ruling.verdict.outcome is Outcome.CONFIRM:
            violations.append(replace(warning, message=f"{warning.message} [confirmed: {ruling.verdict.reason}]"))
    violations.sort(key=attrgetter("position"))
    return replace(report, violations=violations, warnings=warnings)


def _residue_of(warning, analysis: Analysis, by_place: dict) -> Residue | None:
    if warning.path is None:
        return None
    key = (warning.rule, project_path(warning.path, analysis.root), warning.subject, warning.line, warning.column)
    return by_place.get(key)
