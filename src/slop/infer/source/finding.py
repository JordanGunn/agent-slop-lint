"""Residue from the linter's own subjective findings: the warnings.

Only a warning of a rule that has a rubric becomes residue. Its subject is looked up in the
corpus so the excerpt covers the whole definition, not just its first line.
"""
from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from ...violation import Violation
from ..contract import Residue
from ..frame.excerpt import MAX_LINES, excerpt
from ..frame.fingerprint import code_fingerprint, finding_id
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
    path = Path(warning.path)
    if definition is not None:
        node = definition._ast_node()
        first, last = node.line, node.end_line
    else:                                       # not found in the corpus: show from the finding down
        first, last = warning.line, warning.line + MAX_LINES - 1
    shown = excerpt(path, root, first, last)
    question, rubric = rubric_for(warning.rule)
    relative = os.path.relpath(path, root).replace(os.sep, "/")
    return Residue(
        id=finding_id(warning.rule, relative, warning.subject), rule=warning.rule, path=relative,
        line=warning.line, column=warning.column, subject=warning.subject, message=warning.message,
        value=warning.value, threshold=warning.threshold, excerpt=shown, question=question,
        rubric=rubric, fingerprint=code_fingerprint(shown.text, rubric.version))


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
