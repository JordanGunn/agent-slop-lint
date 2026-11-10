"""is_special_method() is a per-grammar fact: only Python treats __x__ names as implicitly invoked."""
from __future__ import annotations

from slop.ast.grammar import GRAMMARS_BY_ID


def test_is_special_method_is_python_only():
    py = GRAMMARS_BY_ID["python"]
    assert py.is_special_method("__init__")
    assert py.is_special_method("__repr__")
    assert not py.is_special_method("plain")
    assert not py.is_special_method("_private")  # single underscore is not a dunder
    # No other language uses the __x__ implicit-dispatch convention: a symbol named
    # __init__ in Go/Rust/etc is an ordinary name, not a special method.
    for gid, grammar in GRAMMARS_BY_ID.items():
        if gid == "python":
            continue
        assert not grammar.is_special_method("__init__"), gid
