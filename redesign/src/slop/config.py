"""Analysis configuration — owned by the ``Corpus``.

The configuration that parameterises a scan: which languages to resolve, which
paths/symbols to ignore, rule thresholds. It is a Corpus-level property because
the Corpus is the analysis boundary; Libraries/Packages/Modules read it through
their owner chain rather than each carrying their own copy.

Placeholder Protocol — the concrete shape is designed alongside the rule layer.
Declared now so ``Corpus.config`` has an honest type and config never gets
threaded in ad-hoc.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class AnalysisConfig(Protocol):
    """Configuration governing a Corpus scan and the rules run over it."""
