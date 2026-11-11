"""The closed question and the rubric for a rule.

A rubric is a bundled reference named ``rubrics/<rule>``. Only a rule that has a question
here and a rubric there can be put to inference. The version is a hash of the rubric's text,
so editing a rubric makes every earlier ruling under it stale.
"""
from __future__ import annotations

from ..bundle import prose
from ..contract import Outcome, Question, RubricRef

#: rule -> (question id, question text). The outcomes are always every Outcome.
_QUESTIONS: dict[str, tuple[str, str]] = {
    "class-cohesion": (
        "class-cohesion.responsibility",
        "Does this class have one responsibility, or does it combine unrelated ones?",
    ),
    "homonym": (
        "homonym.one-meaning",
        "Does this class name mean one thing wherever it is used, or is it overloaded?",
    ),
}


def has_rubric(rule: str) -> bool:
    """True if ``rule`` can be put to inference."""
    return rule in _QUESTIONS and _name(rule) in prose.references()


def rubric_for(rule: str) -> tuple[Question, RubricRef]:
    """The question to ask about a finding of ``rule``, and the rubric that governs it.

    Raises ``KeyError`` for a rule without a rubric."""
    if not has_rubric(rule):
        raise KeyError(rule)
    question_id, text = _QUESTIONS[rule]
    return (Question(id=question_id, text=text, outcomes=tuple(Outcome)),
            RubricRef(command=f"slop infer references {_name(rule)}",
                      version=prose.reference_version(_name(rule))))


def _name(rule: str) -> str:
    return f"rubrics/{rule}"
