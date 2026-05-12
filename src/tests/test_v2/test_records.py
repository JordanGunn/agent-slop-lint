"""Tests for ``slop.tree.records`` — pure-data dataclasses."""
from __future__ import annotations

from pathlib import Path

import pytest

from slop.tree.records import (
    Callable,
    CallableKind,
    Occurrence,
    Parameter,
    ParseResult,
    Scope,
    ScopeKind,
)


class TestParameter:
    def test_basic_construction(self):
        p = Parameter(name="x", position=0)
        assert p.name == "x"
        assert p.position == 0
        assert p.annotation is None

    def test_with_annotation(self):
        p = Parameter(name="cfg", position=1, annotation="SlopConfig")
        assert p.annotation == "SlopConfig"


class TestScope:
    def test_construction_with_required_fields(self):
        s = Scope(qualname="m.Foo", kind=ScopeKind.CLASS, path=Path("m.py"),
                  line=1, end_line=10, parent="m")
        assert s.qualname == "m.Foo"
        assert s.kind == ScopeKind.CLASS

    def test_top_level_has_no_parent(self):
        s = Scope(qualname="m", kind=ScopeKind.FILE, path=Path("m.py"),
                  line=1, end_line=20, parent=None)
        assert s.parent is None

    def test_scope_is_frozen(self):
        s = Scope(qualname="m", kind=ScopeKind.FILE, path=Path("m.py"),
                  line=1, end_line=1, parent=None)
        with pytest.raises((AttributeError, Exception)):
            s.qualname = "other"  # type: ignore[misc]

    def test_no_language_field(self):
        # Records dropped the denormalised language field in the v2 refactor;
        # views maintain the canonical path→language map.
        s = Scope(qualname="m", kind=ScopeKind.FILE, path=Path("m.py"),
                  line=1, end_line=1, parent=None)
        assert not hasattr(s, "language")


class TestCallable:
    def test_callable_uses_parent_not_parent_scope(self):
        # The v2 refactor renamed parent_scope → parent for consistency with Scope.
        c = Callable(qualname="m.foo", kind=CallableKind.FUNCTION, path=Path("m.py"),
                     line=1, end_line=3, parent="m", parameters=())
        assert c.parent == "m"
        assert not hasattr(c, "parent_scope")

    def test_method_carries_parameters(self):
        params = (Parameter(name="self", position=0),
                  Parameter(name="x", position=1, annotation="int"))
        c = Callable(qualname="m.Foo.bar", kind=CallableKind.METHOD,
                     path=Path("m.py"), line=5, end_line=7,
                     parent="m.Foo", parameters=params)
        assert len(c.parameters) == 2
        assert c.parameters[0].name == "self"


class TestOccurrence:
    def test_construction(self):
        o = Occurrence(token="x", path=Path("m.py"), line=2, col=4,
                       scope="m", callable=None, kind="identifier")
        assert o.token == "x"
        assert o.kind == "identifier"


class TestParseResult:
    def test_construction_with_empty_collections(self):
        p = ParseResult(path=Path("a.py"), language="python",
                        scopes=(), callables=(), occurrences=())
        assert p.path == Path("a.py")
        assert p.language == "python"
        assert p.callable_nodes == {}
        assert p.content == b""


class TestEnums:
    def test_scope_kind_values_include_required(self):
        # The substrate-needed kinds — file/class/namespace at minimum.
        required = {"file", "class", "namespace", "module"}
        actual = {k.value for k in ScopeKind}
        assert required.issubset(actual)

    def test_callable_kind_has_all_four(self):
        values = {k.value for k in CallableKind}
        assert values == {"function", "method", "lambda", "constructor"}
