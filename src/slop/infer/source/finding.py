"""Residue from the linter's own subjective findings: the warnings.

STUB: the class is fixed; building residue from a report is not built.
"""
from __future__ import annotations

from collections.abc import Iterator

from ..contract import Residue
from .interface import Analysis, Source


class FindingSource(Source):
    name = "finding"

    def residue(self, analysis: Analysis) -> Iterator[Residue]:
        raise NotImplementedError("infer.source.finding.FindingSource.residue: designed, not built")
