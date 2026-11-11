"""The boundary of storage: what the rest of ``infer`` may ask of a ledger."""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator

from ..contract import Residue, Ruling


class LedgerError(ValueError):
    """The stored record cannot be read. The message names the file and line."""


class Ledger(ABC):
    """An append-only record of rulings. The newest ruling for an id is the one in force."""

    @abstractmethod
    def append(self, ruling: Ruling) -> None:
        """Record ``ruling``. Earlier rulings for the same id stay in the record."""

    @abstractmethod
    def latest(self, finding_id: str) -> Ruling | None:
        """The newest ruling for ``finding_id``, or None."""

    @abstractmethod
    def rulings(self) -> Iterator[Ruling]:
        """Every ruling, oldest first."""

    def current(self, residue: Residue) -> Ruling | None:
        """The ruling in force for ``residue``: the newest for its id, and only if it answered
        the code and rubric as they are now. A ruling on changed code or an edited rubric is
        stale and is not returned."""
        ruling = self.latest(residue.id)
        return ruling if ruling is not None and ruling.fingerprint == residue.fingerprint else None
