"""Apply the ledger's rulings to a lint report, and say where each finding's ruling stands."""
from __future__ import annotations

from dataclasses import dataclass, replace
from operator import attrgetter

from ...dispatch import Report
from ...violation import Violation
from ..contract import Outcome, Residue, Ruling, Status
from ..ledger.interface import Ledger
from ..source.finding import FindingSource
from ..source.interface import Analysis


@dataclass(frozen=True)
class Settlement:
    """The settled report, and the residue of each finding in it that can be put to inference,
    keyed by the finding's ``Violation.position``."""

    report: Report
    residue: dict[tuple[str, int, int, str], Residue]


def settle(analysis: Analysis, ledger: Ledger) -> Settlement:
    """Resolve each warning that has a current ruling, and attach every inferable finding's residue.

    A cleared warning is dropped. A confirmed one becomes a violation, carrying the reason, so it
    fails the run. A deferred warning, a stale ruling and a warning with no ruling stay warnings."""
    report = analysis.report
    inferable = {r.id: r for r in FindingSource().residue(analysis)}
    newest: dict[str, Ruling] = {}
    for ruling in ledger.rulings():
        newest[ruling.verdict.id] = ruling
    violations, warnings = list(report.violations), []
    attached: dict[tuple[str, int, int, str], Residue] = {}
    for warning in report.warnings:
        item = inferable.get(_id(warning, analysis))
        if item is None:
            warnings.append(warning)
            continue
        status = _status(item, newest.get(item.id))
        if status is None:
            continue                                    # cleared: not reported
        if status is Status.CONFIRM:
            ruling = newest[item.id]
            finding = replace(warning, message=f"{warning.message} [confirmed: {ruling.verdict.reason}]")
            violations.append(finding)
        else:
            finding = warning
            warnings.append(finding)
        attached[finding.position] = replace(item, status=status)
    violations.sort(key=attrgetter("position"))
    return Settlement(report=replace(report, violations=violations, warnings=warnings), residue=attached)


def _id(warning: Violation, analysis: Analysis) -> str | None:
    if warning.path is None or warning.subject is None:
        return None
    return warning.id(analysis.root)


def _status(item: Residue, ruling: Ruling | None) -> Status | None:
    """Where ``item``'s ruling stands, or None when it is cleared."""
    if ruling is None:
        return Status.NONE
    if ruling.fingerprint != item.fingerprint:
        return Status.STALE
    return {Outcome.CLEAR: None, Outcome.CONFIRM: Status.CONFIRM, Outcome.DEFER: Status.DEFER}[ruling.verdict.outcome]
