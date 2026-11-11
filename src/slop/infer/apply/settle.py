"""Apply the ledger's rulings to a lint report, and say where each finding's ruling stands."""
from __future__ import annotations

from dataclasses import dataclass, replace
from operator import attrgetter

from ...agglomeration import Agglomeration, agglomerate
from ...dispatch import Report
from ...violation import Violation
from ..contract import Outcome, Residue, Ruling, Status
from ..ledger.interface import Ledger
from ..source.agglomeration import AgglomerationSource
from ..source.finding import FindingSource
from ..source.interface import Analysis


@dataclass(frozen=True)
class Settlement:
    """The settled report; the residue of each finding in it that can be put to inference, keyed
    by the finding's ``Violation.position``; the agglomerations of the settled findings that a
    ruling has not cleared; and the residue of every agglomeration, cleared or not, by its id."""

    report: Report
    residue: dict[tuple[str, int, int, str], Residue]
    agglomerations: tuple[Agglomeration, ...]
    groups: dict[str, Residue]


def settle(analysis: Analysis, ledger: Ledger) -> Settlement:
    """Resolve each warning that has a current ruling, and attach every inferable finding's residue.

    A cleared warning is dropped. A confirmed one becomes a violation, carrying the reason, so it
    fails the run. A deferred warning, a stale ruling and a warning with no ruling stay warnings.
    The settled findings are then grouped; a cleared group is dropped, and a confirmed one is only
    recorded: a group has no location to fail on."""
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
    settled = replace(report, violations=violations, warnings=warnings)
    kept, group_residue = _settle_groups(replace(analysis, report=settled), newest)
    return Settlement(report=settled, residue=attached, agglomerations=kept, groups=group_residue)


def _settle_groups(analysis: Analysis, newest: dict[str, Ruling]) -> tuple[tuple[Agglomeration, ...], dict[str, Residue]]:
    """The groups of the settled findings that no ruling clears, and every group's residue with
    where its ruling stands."""
    groups = tuple(agglomerate([*analysis.report.violations, *analysis.report.warnings], analysis.corpus))
    items = {r.id: r for r in AgglomerationSource(groups).residue(analysis)}
    statuses = {gid: _status(item, newest.get(gid)) for gid, item in items.items()}
    residue = {gid: replace(item, status=statuses[gid] or Status.NONE) for gid, item in items.items()}
    kept = tuple(g for g in groups if g.id not in items or statuses[g.id] is not None)
    return kept, residue


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
