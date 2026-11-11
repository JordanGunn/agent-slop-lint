"""Residue from agglomerations: groups of findings the code's structure relates.

The question is whether a group has one cause. Its residue reads every definition the group
touches, the lead's first; its fingerprint covers that code and the member findings, so a
ruling goes stale when either changes.
"""
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

from ...agglomeration import Agglomeration
from ...identity import ScopeId, project_path
from ..contract import Location, Residue, Status
from ..frame.fingerprint import code_fingerprint, read_lines
from ..frame.rubric import has_rubric, rubric_for
from .interface import Analysis, Source

RULE = "agglomeration"


class AgglomerationSource(Source):
    name = "agglomeration"

    def __init__(self, groups: tuple[Agglomeration, ...]) -> None:
        self._groups = groups

    def residue(self, analysis: Analysis) -> Iterator[Residue]:
        if not has_rubric(RULE):
            return
        question, rubric = rubric_for(RULE)
        scopes = _scopes(analysis.corpus)
        for group in self._groups:
            places = _places(group, scopes)
            locations = tuple(Location(path=project_path(path, analysis.root), first_line=first, last_line=last)
                              for path, first, last in places)
            code = "\n".join(read_lines(Path(path), first, last) for path, first, last in places)
            members = "\n".join(sorted(f.id(analysis.root) for f in group.findings))
            yield Residue(
                id=group.id, rule=RULE, subject=group.lead.qualname, locations=locations,
                question=question, rubric=rubric,
                fingerprint=code_fingerprint(f"{group.topology.value}\n{members}\n{code}", rubric.version),
                status=Status.NONE)


def _places(group: Agglomeration, scopes: dict[ScopeId, Any]) -> list[tuple[str, int, int]]:
    """``(path, first line, last line)`` of the lead's definition and of each member's, once each;
    a member without a definition in a file (a package) is read at the finding's own line."""
    places: dict[tuple[str, int, int], None] = {}
    for scope_id in (group.lead, *(f.scope for f in group.findings)):
        scope = scopes.get(scope_id)
        if scope is not None and scope.files and scope._node is not None:
            node = scope._ast_node()
            places.setdefault((str(scope.files[0]), node.line, node.end_line), None)
    for finding in group.findings:
        if finding.scope not in scopes or scopes[finding.scope]._node is None:
            if finding.path is not None and Path(finding.path).is_file():
                places.setdefault((finding.path, finding.line, finding.line), None)
    return list(places)


def _scopes(corpus: Any) -> dict[ScopeId, Any]:
    found: dict[ScopeId, Any] = {}
    stack = [corpus]
    while stack:
        component = stack.pop()
        found[component.id] = component
        stack.extend(component.children())
    return found
