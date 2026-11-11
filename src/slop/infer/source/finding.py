"""Residue from the linter's own subjective findings: the warnings.

Only a warning of a rule that has a rubric becomes residue. Its subject is looked up in the
corpus, so the span and the fingerprint cover the whole definition, not just its first line.
"""
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

from ...violation import Violation
from ..contract import Residue, Status
from ..frame.fingerprint import code_fingerprint, finding_id
from ..frame.location import project_path
from ..frame.rubric import has_rubric, rubric_for
from .interface import Analysis, Source


class FindingSource(Source):
    name = "finding"

    def residue(self, analysis: Analysis) -> Iterator[Residue]:
        definitions = _definitions(analysis.corpus)
        for warning in analysis.report.warnings:
            if warning.path is None or warning.subject is None or not has_rubric(warning.rule):
                continue
            yield _residue(warning, analysis.root, definitions.get((warning.path, warning.subject)))


def _residue(warning: Violation, root: Path, definition: Any | None) -> Residue:
    if definition is not None:
        node = definition._ast_node()
        first, last = node.line, node.end_line
    else:                                       # not found in the corpus: the finding's own line
        first = last = warning.line
    question, rubric = rubric_for(warning.rule)
    path = project_path(warning.path, root)
    return Residue(
        id=finding_id(warning.rule, path, warning.subject), rule=warning.rule, path=path,
        subject=warning.subject, first_line=first, last_line=last, question=question, rubric=rubric,
        fingerprint=code_fingerprint(_lines(Path(warning.path), first, last), rubric.version),
        status=Status.NONE)


def _lines(path: Path, first: int, last: int) -> str:
    """Lines ``first`` through ``last`` (1-based, inclusive) of ``path``."""
    return "\n".join(path.read_text(encoding="utf-8", errors="replace").splitlines()[first - 1:last])


def _definitions(corpus: Any) -> dict[tuple[str, str], Any]:
    """Every definition in the corpus by (file path, qualified name)."""
    found: dict[tuple[str, str], Any] = {}
    stack = [corpus]
    while stack:
        component = stack.pop()
        if component.files and component.qualname:
            found.setdefault((str(component.files[0]), component.qualname), component)
        stack.extend(component.children())
    return found
