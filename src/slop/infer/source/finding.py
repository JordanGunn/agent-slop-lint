"""Residue from the linter's own subjective findings: the warnings.

Every warning becomes residue: every subjective rule has a rubric (``frame.rubric``). Its subject's extent places it, so a
class or callable shows its whole definition and a package every module in it. A warning is
made at a scope of the corpus (``Violation.at``), so its scope is always found.
"""
from __future__ import annotations

from collections.abc import Iterator

from ...span import Span
from ...violation import Violation
from ..contract import Residue, Status
from ..frame.fingerprint import code_fingerprint
from ..frame.location import code, locations
from ..frame.rubric import rubric_for
from .interface import Analysis, Source, scopes


class FindingSource(Source):
    name = "finding"

    def residue(self, analysis: Analysis) -> Iterator[Residue]:
        found = scopes(analysis.corpus)
        for warning in analysis.report.warnings:
            yield _residue(warning, analysis, found[warning.scope].extent.spans)


def _residue(warning: Violation, analysis: Analysis, spans: tuple[Span, ...]) -> Residue:
    question, rubric = rubric_for(warning.rule)
    return Residue(
        id=warning.id(analysis.root), rule=warning.rule, subject=warning.subject,
        locations=locations(spans, analysis.root), question=question, rubric=rubric,
        fingerprint=code_fingerprint(code(spans), rubric.version), status=Status.NONE)

