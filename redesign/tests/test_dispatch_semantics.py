"""is_dynamic_language() + is_special_method() are per-grammar facts (language-
agnosticism #39), not a hardcoded {python,javascript,ruby} set + __x__ check buried
in the shared orphan / sibling-redundancy compute.

Before the facts, orphans._confidence keyed the dynamic-dispatch penalty off a
hardcoded language set and treated *any* __x__ name as special regardless of
language — so a Go function literally named __init__ was wrongly discounted, and a
TS orphan was scored as more certain than the JS orphan it compiles to.
"""
from __future__ import annotations

from slop.ast.grammar import GRAMMARS_BY_ID
from slop.metrics.structural.orphans import _confidence

# Languages whose runtime dispatch (duck typing / reflection / string-keyed access)
# defeats static reference counting. TS is included: it erases to JS at runtime.
_DYNAMIC = {"python", "javascript", "typescript", "ruby"}


def test_is_dynamic_language_per_grammar():
    for gid, grammar in GRAMMARS_BY_ID.items():
        assert grammar.is_dynamic_language() is (gid in _DYNAMIC), gid


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


def test_dynamic_penalty_is_grammar_driven():
    # Same long, uncommon symbol: a dynamic language caps one tick lower than a static
    # one because static analysis cannot see its runtime dispatch.
    assert _confidence("untouched_routine", GRAMMARS_BY_ID["python"]) == "medium"
    assert _confidence("untouched_routine", GRAMMARS_BY_ID["go"]) == "high"


def test_special_method_low_confidence_python_only():
    # A Python dunder reads as a false orphan (implicitly invoked) → low confidence.
    assert _confidence("__getattr__", GRAMMARS_BY_ID["python"]) == "low"
    # A Go function literally named __getattr__ is not special → scored normally.
    assert _confidence("__getattr__", GRAMMARS_BY_ID["go"]) != "low"
