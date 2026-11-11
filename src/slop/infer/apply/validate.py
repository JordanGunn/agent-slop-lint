"""Check verdicts against the worklist they answer.

STUB: the signature is fixed; checking is not built. A verdict is rejected when its id is not
in the outstanding worklist, or when it uses an outcome its question does not allow.
"""
from __future__ import annotations

from collections.abc import Mapping

from ..contract import Rejection, Residue, Verdicts


def validate(verdicts: Verdicts, outstanding: Mapping[str, Residue]) -> tuple[Rejection, ...]:
    """The verdicts in ``verdicts`` that cannot be accepted against ``outstanding``, by id."""
    raise NotImplementedError("infer.apply.validate.validate: designed, not built")
