"""The closed question and the rubric for a rule.

STUB: the signature is fixed; loading rubrics is not built. A rubric is package data, one
file per rule; its version is a hash of its content.
"""
from __future__ import annotations

from ..contract import Question, RubricRef


def rubric_for(rule: str) -> tuple[Question, RubricRef]:
    """The question to ask about a finding of ``rule``, and the rubric that governs it."""
    raise NotImplementedError("infer.frame.rubric.rubric_for: designed, not built")
