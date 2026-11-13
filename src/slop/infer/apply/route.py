"""Store the accepted verdicts, end the rulings whose finding is gone, and answer with a receipt."""
from __future__ import annotations

from collections.abc import Callable, Mapping

from ..contract import SCHEMA_VERSION, Receipt, Residue, Ruling, Verdicts
from ..ledger.interface import Ledger
from .validate import validate


def route(verdicts: Verdicts, residue: Mapping[str, Residue], ledger: Ledger, *, at: str,
          scanned: Callable[[Ruling], bool]) -> Receipt:
    """Store each acceptable verdict in ``ledger``, stamped ``at``, and report the result.

    ``residue`` is every current finding that can be ruled on. A stored ruling whose finding is
    not among them has nothing left to answer, and it ends, but only where ``scanned`` says the
    analysis covered its code: scanning one directory says nothing about findings elsewhere. An
    accepted verdict replaces any earlier ruling for its id."""
    rejections = validate(verdicts, residue)
    refused = {r.id for r in rejections}
    kept = {r.verdict.id: r for r in ledger.rulings()}
    ended = tuple(sorted(i for i, r in kept.items() if i not in residue and scanned(r)))
    for finding_id in ended:
        del kept[finding_id]
    accepted: list[str] = []
    for verdict in verdicts.verdicts:
        if verdict.id in refused:
            continue
        item = residue[verdict.id]
        kept[verdict.id] = Ruling(verdict=verdict, rule=item.rule, path=item.locations[0].path,
                                  fingerprint=item.fingerprint, rubric_version=item.rubric.version, at=at)
        accepted.append(verdict.id)
    ledger.write(kept.values())
    return Receipt(version=SCHEMA_VERSION, accepted=tuple(accepted), rejected=rejections, ended=ended)
