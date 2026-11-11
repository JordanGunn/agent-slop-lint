"""Apply the ledger's rulings to a lint report.

STUB: the signature is fixed; settling is not built. A cleared warning is dropped; a
confirmed one becomes a violation; a deferred or stale one stays a warning.
"""
from __future__ import annotations

from ...dispatch import Report
from ..ledger.interface import Ledger


def settle(report: Report, ledger: Ledger) -> Report:
    """``report`` with each finding that has a current ruling in ``ledger`` resolved by it."""
    raise NotImplementedError("infer.apply.settle.settle: designed, not built")
