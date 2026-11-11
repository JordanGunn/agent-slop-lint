"""Ruby locals are ordered; method names are visible in their class throughout its body."""
from __future__ import annotations

from pathlib import Path

from slop.ast import GRAMMARS_BY_ID
from slop.ast.binding import SymbolKind, bind
from slop.ast.tree import AST

_SOURCE = """\
class Widget
  def run(p, q=1, k:, *rest, &blk)
    early
    early = p
    obj.foo(k: q)
    @x = early
    [1].each do |v|
      v + early
      inner = v
    end
    f = ->(z) { z + early }
    [1].each { |early| early + p }
    for item in rest do
      item
    end
    helper
    @x
  end
  def helper
    1
  end
  def self.utility(z)
    z
  end
end
"""


def _bindings(tmp_path: Path):
    path = tmp_path / "widget.rb"
    path.write_text(_SOURCE, encoding="utf-8")
    grammar, content = GRAMMARS_BY_ID["ruby"], path.read_bytes()
    found = {}
    for occurrence in bind(AST.parse(path, grammar).root.raw, content, grammar).values():
        key = (occurrence.text, content[:occurrence.start].count(b"\n") + 1)
        found.setdefault(key, []).append(occurrence)
    return found, content


def test_parameters_ordered_locals_and_closures(tmp_path: Path):
    found, content = _bindings(tmp_path)
    def role(text: str, line: int) -> list:
        return [b.kind for b in found[(text, line)]]
    assert role("early", 3) == [SymbolKind.FREE]
    assert role("early", 4) == [SymbolKind.LOCAL]
    assert role("p", 4) == [SymbolKind.PARAMETER]
    assert role("q", 5) == [SymbolKind.PARAMETER]
    assert role("v", 8) == [SymbolKind.PARAMETER]
    assert role("early", 8) == [SymbolKind.LOCAL]
    assert role("z", 11) == [SymbolKind.PARAMETER, SymbolKind.PARAMETER]
    assert role("early", 11) == [SymbolKind.LOCAL]
    assert role("early", 12) == [SymbolKind.PARAMETER, SymbolKind.PARAMETER]
    assert role("p", 12) == [SymbolKind.PARAMETER]
    assert role("item", 14) == [SymbolKind.LOCAL]
    assert {text: role(text, 2) for text in ("p", "q", "k", "rest", "blk")} == {
        text: [SymbolKind.PARAMETER] for text in ("p", "q", "k", "rest", "blk")
    }
    assert content[:found[("early", 8)][0].definition].count(b"\n") + 1 == 4
    assert ("foo", 5) not in found and ("k", 5) not in found and ("each", 7) not in found


def test_fields_methods_and_singleton_methods(tmp_path: Path):
    found, _ = _bindings(tmp_path)
    assert [b.kind for b in found[("@x", 6)]] == [SymbolKind.FIELD]
    assert found[("@x", 6)][0].defines
    assert [b.kind for b in found[("@x", 17)]] == [SymbolKind.FIELD]
    assert [b.kind for b in found[("helper", 16)]] == [SymbolKind.METHOD]
    assert [b.kind for b in found[("helper", 19)]] == [SymbolKind.METHOD]
    assert [b.kind for b in found[("utility", 22)]] == [SymbolKind.METHOD]
    assert [b.kind for b in found[("z", 23)]] == [SymbolKind.PARAMETER]
