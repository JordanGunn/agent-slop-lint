"""Go bindings: receiver parameters, ordered declarations, blocks and closures."""
from __future__ import annotations

from pathlib import Path

from slop.ast import GRAMMARS_BY_ID
from slop.ast.binding import SymbolKind, bind
from slop.ast.tree import AST

_SOURCE = """\
package main
type Point struct { x int }
var global int
func outer(p int) int {
    early := global
    unseen := later
    global := p
    later := 2
    x, extra := global, 3
    var q, r int = x, extra
    for i := 0; i < 2; i++ { x := i; _ = x }
    for idx, value := range []int{x} { _ = idx; _ = value }
    closure := func(z int) int { x := z; return x + q }
    pt := Point{x: x}
    _ = pt.x
    return early + unseen + r + closure(1) + map[int]int{x: 1}[x]
}
func (s *Point) method(arg int) int { local := s.x + arg; return local }
"""


def _bindings(tmp_path: Path):
    path = tmp_path / "m.go"
    path.write_text(_SOURCE, encoding="utf-8")
    content = path.read_bytes()
    grammar = GRAMMARS_BY_ID["go"]
    found = {}
    for occurrence in bind(AST.parse(path, grammar).root.raw, content, grammar).values():
        key = (occurrence.text, content[:occurrence.start].count(b"\n") + 1)
        found.setdefault(key, []).append(occurrence)
    return found


def test_receiver_parameters_and_ordered_names(tmp_path: Path):
    b = _bindings(tmp_path)
    assert b["x", 2][0].defines and b["x", 2][0].kind is SymbolKind.FIELD
    assert b["p", 7][0].kind is SymbolKind.PARAMETER
    assert b["s", 18][0].kind is SymbolKind.PARAMETER
    assert b["arg", 18][-1].kind is SymbolKind.PARAMETER
    assert b["global", 5][0].definition == b["global", 3][0].start
    assert b["global", 9][0].definition == b["global", 7][0].start
    assert b["later", 6][0].kind is SymbolKind.FREE
    assert b["q", 13][0].definition == b["q", 10][0].start
    assert b["r", 16][0].definition == b["r", 10][0].start


def test_blocks_loops_and_closure_capture(tmp_path: Path):
    b = _bindings(tmp_path)
    assert b["x", 11][-1].definition == b["x", 11][0].start
    assert [v.kind for v in b["idx", 12]] == [SymbolKind.LOCAL, SymbolKind.LOCAL]
    assert [v.kind for v in b["value", 12]] == [SymbolKind.LOCAL, SymbolKind.LOCAL]
    assert b["x", 12][0].definition == b["x", 9][0].start
    assert [v.kind for v in b["z", 13]] == [SymbolKind.PARAMETER, SymbolKind.PARAMETER]
    assert b["x", 13][-1].definition == b["x", 13][0].start
    assert b["q", 13][0].definition == b["q", 10][0].start
    assert len(b["x", 14]) == 1  # literal value, not its keyed field
    assert b["x", 14][0].definition == b["x", 9][0].start
    assert ("x", 15) not in b  # selector field_identifier is not a variable
    assert [v.kind for v in b["x", 16]] == [SymbolKind.LOCAL, SymbolKind.LOCAL]  # map key is a use
    assert ("_", 15) not in b
