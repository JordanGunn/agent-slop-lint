"""Tests for the Python concrete grammar."""
from __future__ import annotations

from slop.language.grammars import Python


class TestPythonNodeTypeSets:
    def test_callable_includes_function_and_lambda(self):
        c = Python.callable()
        assert "function_definition" in c
        assert "async_function_definition" in c
        assert "lambda" in c

    def test_classes_returns_class_definition(self):
        assert Python.classes() == frozenset({"class_definition"})

    def test_methods_excludes_lambda(self):
        # Lambdas can't be methods in Python.
        methods = Python.methods()
        assert "function_definition" in methods
        assert "lambda" not in methods

    def test_id_is_python(self):
        assert Python.id == "python"
