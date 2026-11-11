"""Check verdicts against the findings they answer."""
from __future__ import annotations

from collections import Counter
from collections.abc import Mapping

from ..contract import Rejection, Residue, Verdicts


def validate(verdicts: Verdicts, residue: Mapping[str, Residue]) -> tuple[Rejection, ...]:
    """The verdicts that cannot be accepted, in document order.

    A verdict is rejected when its id is not a finding in ``residue``, when its outcome is not
    one its question allows, or when its id appears more than once in the document: the
    agent must say which answer it means."""
    seen = Counter(v.id for v in verdicts.verdicts)
    rejected: list[Rejection] = []
    for verdict in verdicts.verdicts:
        item = residue.get(verdict.id)
        if seen[verdict.id] > 1:
            reason = "this id appears more than once in the document"
        elif item is None:
            reason = "no such finding: no current lint finding with a residue has this id"
        elif verdict.outcome not in item.question.outcomes:
            reason = f"outcome '{verdict.outcome.value}' is not allowed for this question"
        else:
            continue
        rejected.append(Rejection(id=verdict.id, reason=reason))
    return tuple(rejected)
