"""slop.scope: the tree slop carves the sources into, and the queries over it.

    Corpus -> Realm -> Package -> Module -> Class -> Callable

``scan_corpus`` builds the tree; ``model`` holds the scope classes; ``identity`` the ids,
kinds and extents; ``find`` looks scopes up by name. Measurements live in
``slop.metrics.structural`` and are read through ``Structure.over(scope)``.
"""
from __future__ import annotations

from .carve import scan_corpus
from .identity import CallableKind, Extent, ScopeId, ScopeKind, Span
from .model import Callable, Class, Corpus, Module, Package, Realm, Scope

__all__ = [
    "scan_corpus",
    "Scope",
    "Corpus",
    "Realm",
    "Package",
    "Module",
    "Class",
    "Callable",
    "ScopeId",
    "ScopeKind",
    "CallableKind",
    "Extent",
    "Span",
]
