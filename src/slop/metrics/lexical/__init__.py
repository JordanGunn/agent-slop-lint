"""slop's lexical signals — the linguistic twin of ``metrics/structural``.

The AST/scope-dependent measurements the lexical rules consume live on a
``Lexical.over(region)`` view (added incrementally); the self-contained compute
(affix/FCA token clustering, packet ownership filtering, cluster profiling) lives in
sibling modules, ported from the legacy ``src/slop/lexicon`` compute.

Pure token-space queries (token locations, frequency head) stay on the ``Lexicon``
kernel itself — they need only tokens+spans, not the AST — keeping this layer the
home of only the structure-aware lexical signals.
"""
from __future__ import annotations

from . import affix, filters
from .records import FirstParameterCluster, NamedEntity
from .view import Lexical

__all__ = ["Lexical", "affix", "filters", "FirstParameterCluster", "NamedEntity"]
