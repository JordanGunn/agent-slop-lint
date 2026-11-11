"""A verdict slop accepted, with the provenance that keeps it honest.

A ``Ruling`` is one line of the ledger. It is stale when the code under it or the rubric
behind it has changed, which ``fingerprint`` and ``rubric_version`` record.
"""
from __future__ import annotations

from dataclasses import dataclass

from .schema import described
from .verdict import Verdict


@dataclass(frozen=True)
class Ruling:
    """An accepted verdict and where it came from."""

    verdict: Verdict = described("The accepted verdict.")
    rule: str = described("The rule the finding came from.")
    path: str = described("Path relative to the project root, for a human reading a diff.")
    fingerprint: str = described("The residue fingerprint the verdict answered.")
    rubric_version: str = described("The version of the rubric the verdict was given under.")
    at: str = described("When it was accepted, ISO 8601 UTC.")
