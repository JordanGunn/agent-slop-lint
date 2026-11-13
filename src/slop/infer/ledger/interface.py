"""The boundary of storage: what the rest of ``infer`` may ask of a ledger."""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable, Iterator

from ..contract import Ruling


class LedgerError(ValueError):
    """The stored record cannot be read. The message names the file and line."""


class Ledger(ABC):
    """The rulings of a project, at most one per finding id: each one in force, or stale and
    waiting to be ruled again. A ruling whose finding is gone has ended and is not kept; the
    record's history is the version control of the file that holds it."""

    @abstractmethod
    def rulings(self) -> Iterator[Ruling]:
        """Every ruling. Should the record hold two for one id, the later one is in force."""

    @abstractmethod
    def write(self, rulings: Iterable[Ruling]) -> None:
        """Replace the record with ``rulings``."""
