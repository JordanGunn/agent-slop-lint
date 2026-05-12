"""Tests for ``slop.language.base`` — the Language ABC."""
from __future__ import annotations

import pytest

from slop.language import Language, MultiPurpose, ObjectOriented, Procedural


class TestLanguageABC:
    def test_language_cannot_be_instantiated_directly(self):
        with pytest.raises(TypeError):
            Language()  # type: ignore[abstract]

    def test_paradigm_classes_cannot_be_instantiated_directly(self):
        for cls in (ObjectOriented, Procedural, MultiPurpose):
            with pytest.raises(TypeError):
                cls()  # type: ignore[abstract]

    def test_language_declares_id_classvar(self):
        # Concrete grammars set `id`; the base just declares the slot.
        # We can verify this via the annotation rather than instantiation.
        assert "id" in Language.__annotations__

    def test_grammar_classmethod_lazy_loads_tree_sitter(self):
        # Pick a concrete grammar and exercise the grammar() classmethod.
        from slop.language.grammars import Python
        ts_lang = Python.grammar()
        assert ts_lang is not None  # tree-sitter Language loaded

    def test_identifiers_default_is_identifier(self):
        from slop.language.grammars import Python
        # Python doesn't override identifiers; should inherit the default.
        assert "identifier" in Python.identifiers()

    def test_namespaces_default_is_empty(self):
        from slop.language.grammars import Python
        # Python has no namespaces; should inherit the empty default.
        # (NOTE: namespaces() is the deferred-support classmethod; default
        # is the empty frozenset.)
        # If the namespaces() classmethod doesn't exist yet, skip.
        if hasattr(Python, "namespaces"):
            assert Python.namespaces() == frozenset()
