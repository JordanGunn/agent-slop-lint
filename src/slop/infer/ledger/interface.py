"""The boundary of storage: what the rest of ``infer`` may ask of a ledger."""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator

from ..contract import Ruling


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
