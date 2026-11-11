"""Store the accepted verdicts and answer with a receipt."""
from __future__ import annotations

from collections.abc import Mapping

from ..contract import SCHEMA_VERSION, Receipt, Residue, Ruling, Verdicts
from ..ledger.interface import Ledger
from .validate import validate


def route(verdicts: Verdicts, residue: Mapping[str, Residue], ledger: Ledger, *, at: str) -> Receipt:
    """Append each acceptable verdict to ``ledger``, stamped ``at``, and report the result.

    Every verdict is either accepted or rejected with a reason. Accepted verdicts are stored
    in document order."""
    rejections = validate(verdicts, residue)
    refused = {r.id for r in rejections}
    accepted: list[str] = []
    for verdict in verdicts.verdicts:
        if verdict.id in refused:
            continue
        item = residue[verdict.id]
        ledger.append(Ruling(verdict=verdict, rule=item.rule, path=item.locations[0].path, fingerprint=item.fingerprint,
                             rubric_version=item.rubric.version, at=at))
        accepted.append(verdict.id)
    return Receipt(version=SCHEMA_VERSION, accepted=tuple(accepted), rejected=rejections)
