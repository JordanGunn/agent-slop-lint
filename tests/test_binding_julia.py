"""Julia parameters, hoisted locals, lexical loops, lets, closures, and struct fields."""
from __future__ import annotations

from pathlib import Path

from slop.ast import GRAMMARS_BY_ID
from slop.ast.binding import SymbolKind, bind
from slop.ast.tree import AST

_SOURCE = """\
struct Box
    value::Int
end
function compute(p::Int, q=1)
    early
    early = p
    for i in 1:2
        inner = i + early
    end
    let z = early
        z + p
    end
    let p = q
        p + early
    end
    f = x -> x + early
    pair = (a, b) -> a + b
    map([1]) do y
        y + early
    end
    obj.value
    return q
end
"""


def _bindings(tmp_path: Path):
    path = tmp_path / "module.jl"
    path.write_text(_SOURCE, encoding="utf-8")
    grammar, content = GRAMMARS_BY_ID["julia"], path.read_bytes()
    found = {}
    for occurrence in bind(AST.parse(path, grammar).root.raw, content, grammar).values():
        key = (occurrence.text, content[:occurrence.start].count(b"\n") + 1)
        found.setdefault(key, []).append(occurrence)
    return found, content


def test_function_hoisting_and_nested_scopes(tmp_path: Path):
    found, content = _bindings(tmp_path)
    def role(text: str, line: int) -> list:
        return [b.kind for b in found[(text, line)]]
    assert role("p", 4) == [SymbolKind.PARAMETER]
    assert role("q", 4) == [SymbolKind.PARAMETER]
    assert role("early", 5) == [SymbolKind.LOCAL]
    assert content[:found[("early", 5)][0].definition].count(b"\n") + 1 == 6
    assert role("p", 6) == [SymbolKind.PARAMETER]
    assert role("i", 8) == [SymbolKind.LOCAL]
    assert role("early", 8) == [SymbolKind.LOCAL]
    assert role("z", 11) == [SymbolKind.LOCAL]
    assert role("p", 11) == [SymbolKind.PARAMETER]
    assert role("p", 14) == [SymbolKind.LOCAL]
    assert role("q", 13) == [SymbolKind.PARAMETER]
    assert role("x", 16) == [SymbolKind.PARAMETER, SymbolKind.PARAMETER]
    assert role("early", 16) == [SymbolKind.LOCAL]
    assert role("a", 17) == [SymbolKind.PARAMETER, SymbolKind.PARAMETER]
    assert role("b", 17) == [SymbolKind.PARAMETER, SymbolKind.PARAMETER]
    assert role("y", 19) == [SymbolKind.PARAMETER]
    assert role("early", 19) == [SymbolKind.LOCAL]
    assert role("q", 22) == [SymbolKind.PARAMETER]


def test_struct_field_and_receiver_name(tmp_path: Path):
    found, _ = _bindings(tmp_path)
    assert [b.kind for b in found[("value", 2)]] == [SymbolKind.FIELD]
    assert found[("value", 2)][0].defines
    assert ("Int", 2) not in found and ("Int", 4) not in found
    assert ("value", 21) not in found
    assert [b.kind for b in found[("obj", 21)]] == [SymbolKind.FREE]
