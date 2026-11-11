"""What still needs the agent: findings with no current ruling."""
from __future__ import annotations

from ..contract import SCHEMA_VERSION, Worklist
from ..ledger.interface import Ledger
from ..source.finding import FindingSource
from ..source.interface import Analysis


def outstanding(analysis: Analysis, ledger: Ledger, *, rule: str | None = None,
                limit: int | None = None) -> Worklist:
    """The worklist of findings that have no current ruling, optionally of one ``rule`` and at
    most ``limit`` items. A finding ruled on before its code or rubric changed is outstanding again."""
    items = [r for r in FindingSource().residue(analysis)
             if ledger.current(r) is None and rule in (None, r.rule)]
    return Worklist(version=SCHEMA_VERSION, items=tuple(items[:limit]))
