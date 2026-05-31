"""Concrete realisation of the component interfaces — carving + components.

``Corpus.scan(root, config)`` (via ``carve.scan_corpus``) is the entry point;
it returns a concrete ``Corpus`` whose hierarchy answers the metrics.
"""
from __future__ import annotations

from .carve import scan_corpus
from .components import Callable, Class, Corpus, Module, Package, Realm

__all__ = ["scan_corpus", "Corpus", "Realm", "Package", "Module", "Class", "Callable"]
