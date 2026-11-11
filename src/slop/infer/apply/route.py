"""Store the accepted verdicts and answer with a receipt.

STUB: the signature is fixed; routing is not built.
"""
from __future__ import annotations

from collections.abc import Mapping

from ..contract import Receipt, Residue, Verdicts
from ..ledger.interface import Ledger


def route(verdicts: Verdicts, outstanding: Mapping[str, Residue], ledger: Ledger) -> Receipt:
    """Append each acceptable verdict to ``ledger`` and report what was accepted or rejected."""
    raise NotImplementedError("infer.apply.route.route: designed, not built")
