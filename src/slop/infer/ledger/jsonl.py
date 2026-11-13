"""A ledger kept as one JSON object per line in a file under the project's state directory.

The file is meant to be committed: one ruling per line, in a stable order, makes a change a
readable diff and lets two branches merge. A line that cannot be read is an error, not something to skip, so a
lost ruling is never silent.
"""
from __future__ import annotations

import json
from collections.abc import Iterable, Iterator
from pathlib import Path

from ...layout import STATE_DIR
from ..contract import ContractError, Ruling, dump, parse
from .interface import Ledger, LedgerError

LEDGER_FILENAME = "inferences.jsonl"


class JsonlLedger(Ledger):
    def __init__(self, path: Path) -> None:
        self.path = path

    @classmethod
    def at(cls, root: Path) -> JsonlLedger:
        """The ledger of the project at ``root``."""
        return cls(root / STATE_DIR / LEDGER_FILENAME)

    def write(self, rulings: Iterable[Ruling]) -> None:
        """One line per ruling, ordered by path, rule and id, so a change is a small diff. An
        empty record removes the file. The file is replaced whole, never left half written."""
        ordered = sorted(rulings, key=lambda r: (r.path, r.rule, r.verdict.id))
        if not ordered:
            self.path.unlink(missing_ok=True)
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        staged = self.path.with_suffix(".jsonl.tmp")
        staged.write_text("".join(json.dumps(dump(r), ensure_ascii=False) + "\n" for r in ordered), encoding="utf-8")
        staged.replace(self.path)

    def rulings(self) -> Iterator[Ruling]:
        if not self.path.exists():
            return
        with self.path.open(encoding="utf-8") as lines:
            for number, line in enumerate(lines, 1):
                if not line.strip():
                    continue
                try:
                    yield parse(Ruling, json.loads(line))
                except (json.JSONDecodeError, ContractError) as exc:
                    raise LedgerError(f"{self.path}:{number}: {exc}") from exc
