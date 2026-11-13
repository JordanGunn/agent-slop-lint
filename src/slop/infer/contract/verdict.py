"""What the agent returns, and what slop answers.

``Verdicts`` is the document an agent writes: one ``Verdict`` per finding it ruled on.
``Receipt`` is slop's answer: which ids it accepted and which it rejected, and why.
"""
from __future__ import annotations

from dataclasses import dataclass

from .schema import described
from .vocabulary import REASON_MAX_LENGTH, SCHEMA_VERSION, Outcome


@dataclass(frozen=True)
class Verdict:
    """The agent's decision on one finding."""

    id: str = described("The id of the finding, copied from its residue.", min_length=1)
    outcome: Outcome = described("clear: not a problem here. confirm: a real problem. "
                                 "defer: not decidable from the code.")
    reason: str = described("One sentence of evidence from the code.", max_length=REASON_MAX_LENGTH)


@dataclass(frozen=True)
class Verdicts:
    """The document `slop infer apply` reads."""

    version: str = described("The document version.", const=SCHEMA_VERSION)
    verdicts: tuple[Verdict, ...] = described("One verdict per finding ruled on.")


@dataclass(frozen=True)
class Rejection:
    """A verdict slop did not accept."""

    id: str = described("The id of the rejected verdict.")
    reason: str = described("Why it was rejected, as a sentence.")


@dataclass(frozen=True)
class Receipt:
    """What `slop infer apply` answers: every verdict is either accepted or rejected."""

    version: str = described("The document version.", const=SCHEMA_VERSION)
    accepted: tuple[str, ...] = described("Ids of verdicts stored in the ledger.")
    rejected: tuple[Rejection, ...] = described("Verdicts that were not stored, with the reason.")
    ended: tuple[str, ...] = described(
        "Ids of rulings removed from the ledger because their finding no longer exists in the scanned code.")
