"""Tests for the paradigm hierarchy MRO + defaults + override mechanics."""
from __future__ import annotations

from slop.language import Language, MultiPurpose, ObjectOriented, Procedural
from slop.language.grammars import C, CSharp, Cpp, Java, Julia, Python


class TestMRO:
    def test_multipurpose_inherits_both_paradigms(self):
        assert issubclass(MultiPurpose, ObjectOriented)
        assert issubclass(MultiPurpose, Procedural)
        assert issubclass(MultiPurpose, Language)

    def test_python_mro_order(self):
        mro_names = [c.__name__ for c in Python.__mro__]
        # Python → MultiPurpose → ObjectOriented → Procedural → Language → ABC → object
        assert mro_names[0] == "Python"
        assert "MultiPurpose" in mro_names
        assert "ObjectOriented" in mro_names
        assert "Procedural" in mro_names
        assert "Language" in mro_names

    def test_oo_only_language_is_not_procedural(self):
        # Java inherits ObjectOriented but NOT Procedural.
        assert issubclass(Java, ObjectOriented)
        assert not issubclass(Java, Procedural)
        assert not issubclass(Java, MultiPurpose)

    def test_procedural_only_language_is_not_oo(self):
        assert issubclass(C, Procedural)
        assert not issubclass(C, ObjectOriented)
        assert issubclass(Julia, Procedural)
        assert not issubclass(Julia, ObjectOriented)


class TestParadigmDefaults:
    def test_methods_default_to_callable_set(self):
        # Java doesn't override methods(); inherits the default
        # `cls.callable()` from ObjectOriented.
        assert Java.methods() == Java.callable()

    def test_functions_default_to_callable_set(self):
        # C is Procedural-only; functions() defaults to callable().
        assert C.functions() == C.callable()

    def test_python_overrides_methods_to_exclude_lambda(self):
        # Lambdas can't be methods in Python; the override removes them.
        assert "lambda" in Python.callable()
        assert "lambda" not in Python.methods()


class TestConcreteSurface:
    def test_all_grammars_declare_id(self):
        for cls in (Python, Java, Cpp, C, CSharp, Julia):
            assert isinstance(cls.id, str) and cls.id  # truthy

    def test_oo_grammars_declare_classes(self):
        # Both OO-only and MultiPurpose grammars must declare classes().
        for cls in (Python, Java, Cpp, CSharp):
            assert cls.classes()  # non-empty frozenset

    def test_csharp_id_matches_tree_sitter_package_suffix(self):
        # C# is the language with a snake-case tree-sitter package suffix.
        assert CSharp.id == "c_sharp"
