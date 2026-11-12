"""Residue from agglomerations: groups of findings the code's structure relates.

The question is whether a group has one cause. Its residue reads the extent of every unit the
group sits on (a class, a function, a module, a package), the lead's first; its fingerprint covers that code and the member findings, so a
ruling goes stale when either changes.
"""
from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from ...agglomeration import Agglomeration
from ...identity import ScopeId
from ...span import Span
from ..contract import Residue, Status
from ..frame.fingerprint import code_fingerprint
from ..frame.location import code, locations
from ..frame.rubric import rubric_for
from .interface import Analysis, Source, scopes

RULE = "agglomeration"


class AgglomerationSource(Source):
    name = "agglomeration"

    def __init__(self, groups: tuple[Agglomeration, ...]) -> None:
        self._groups = groups

    def residue(self, analysis: Analysis) -> Iterator[Residue]:
        question, rubric = rubric_for(RULE)
        found = scopes(analysis.corpus)
        for group in self._groups:
            spans = _spans(group, found)
            members = "\n".join(sorted(f.id(analysis.root) for f in group.findings))
            yield Residue(
                id=group.id, rule=RULE, subject=group.lead.qualname,
                locations=locations(spans, analysis.root), question=question, rubric=rubric,
                fingerprint=code_fingerprint(f"{group.topology.value}\n{members}\n{code(spans)}", rubric.version),
                status=Status.NONE)


def _spans(group: Agglomeration, found: dict[ScopeId, Any]) -> list[Span]:
    """The extent of the lead, then of every other unit the group sits on."""
    spans: list[Span] = []
    for unit in dict.fromkeys((group.lead, *group.units)):
        spans.extend(found[unit].extent.spans)
    return spans
