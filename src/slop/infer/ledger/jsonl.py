"""A ledger kept as one JSON object per line in a file under the project's state directory.

STUB: the location is fixed; reading and writing are not built.
"""
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from ...layout import STATE_DIR
from ..contract import Ruling
from .interface import Ledger

LEDGER_FILENAME = "inferences.jsonl"


class JsonlLedger(Ledger):
    def __init__(self, path: Path) -> None:
        self.path = path

    @classmethod
    def at(cls, root: Path) -> JsonlLedger:
        """The ledger of the project at ``root``."""
        return cls(root / STATE_DIR / LEDGER_FILENAME)

    def append(self, ruling: Ruling) -> None:
        raise NotImplementedError("infer.ledger.jsonl.append: designed, not built")

    def latest(self, finding_id: str) -> Ruling | None:
        raise NotImplementedError("infer.ledger.jsonl.latest: designed, not built")

    def rulings(self) -> Iterator[Ruling]:
        raise NotImplementedError("infer.ledger.jsonl.rulings: designed, not built")
