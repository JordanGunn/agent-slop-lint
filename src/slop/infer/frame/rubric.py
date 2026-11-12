"""The closed question and the rubric for a rule.

A rubric is a bundled reference named ``rubrics/<rule>``. Every subjective rule ships one, so
every warning can be put to inference; a warning that could never be ruled on would stay a
warning forever. The rubric states its one question on a line of its own,
``Question: ...``; the outcomes are always every ``Outcome``. The version is a hash of the
rubric's text, so editing a rubric makes every earlier ruling under it stale.
"""
from __future__ import annotations

from ..bundle import prose
from ..contract import Outcome, Question, RubricRef

_QUESTION = "Question:"


def rubric_for(rule: str) -> tuple[Question, RubricRef]:
    """The question to ask about a finding of ``rule``, and the rubric that governs it.

    Raises ``KeyError`` for a rule without a rubric, and ``ValueError`` for a rubric that does
    not state its question."""
    name = _name(rule)
    if name not in prose.references():
        raise KeyError(rule)
    return (Question(id=rule, text=_question(name), outcomes=tuple(Outcome)),
            RubricRef(command=f"slop infer references {name}", version=prose.reference_version(name)))


def _question(name: str) -> str:
    for line in prose.reference(name).splitlines():
        if line.startswith(_QUESTION):
            return line.removeprefix(_QUESTION).strip()
    raise ValueError(f"rubric {name} states no '{_QUESTION}' line")


def _name(rule: str) -> str:
    return f"rubrics/{rule}"
