"""Rust bindings: ordered lets, patterns, match arms and closures."""
from __future__ import annotations

from pathlib import Path

from slop.ast import GRAMMARS_BY_ID
from slop.ast.binding import SymbolKind, bind
from slop.ast.tree import AST

_SOURCE = """\
struct Point { x: i32, y: i32 }
fn outer(p: i32) -> i32 {
    let x = p;
    let before = later;
    let later = 2;
    let (a, b) = (x, later);
    let Point { x: field_x, y } = Point { x: a, y: b };
    for i in [x] { let x = i; let _ = x; }
    let closure = |z: i32| { let x = z; x + a };
    let result = match x { v if v > 0 => v, _ => b };
    if let Some(value) = Some(result) { let _ = value; }
    let pt = Point { x: closure(1), y: field_x };
    let _ = pt.x;
    before + result + pt.y
}
"""


def _bindings(tmp_path: Path):
    path = tmp_path / "m.rs"
    path.write_text(_SOURCE, encoding="utf-8")
    content = path.read_bytes()
    grammar = GRAMMARS_BY_ID["rust"]
    found = {}
    for occurrence in bind(AST.parse(path, grammar).root.raw, content, grammar).values():
        key = (occurrence.text, content[:occurrence.start].count(b"\n") + 1)
        found.setdefault(key, []).append(occurrence)
    return found


def test_let_patterns_and_ordered_bindings(tmp_path: Path):
    b = _bindings(tmp_path)
    assert all(v.defines and v.kind is SymbolKind.FIELD for v in (b["x", 1][0], b["y", 1][0]))
    assert b["p", 3][0].kind is SymbolKind.PARAMETER
    assert b["later", 4][0].kind is SymbolKind.FREE
    assert b["later", 6][0].definition == b["later", 5][0].start
    assert b["a", 7][0].definition == b["a", 6][0].start
    assert b["b", 7][0].definition == b["b", 6][0].start
    assert b["field_x", 12][0].definition == b["field_x", 7][0].start
    assert b["y", 7][0].defines
    assert ("x", 7) not in b  # struct field names aren't variables


def test_loop_shadowing_closure_and_match_arm(tmp_path: Path):
    b = _bindings(tmp_path)
    assert b["i", 8][-1].definition == b["i", 8][0].start
    assert b["x", 8][0].definition == b["x", 3][0].start
    assert b["x", 8][-1].definition == b["x", 8][1].start
    assert [v.kind for v in b["z", 9]] == [SymbolKind.PARAMETER, SymbolKind.PARAMETER]
    assert b["x", 9][-1].definition == b["x", 9][0].start
    assert b["a", 9][0].definition == b["a", 6][0].start
    assert [v.kind for v in b["v", 10]] == [SymbolKind.LOCAL, SymbolKind.LOCAL, SymbolKind.LOCAL]
    assert all(v.definition == b["v", 10][0].start for v in b["v", 10])
    assert b["value", 11][-1].definition == b["value", 11][0].start
    assert [v.kind for v in b["Some", 11]] == [SymbolKind.FREE]  # constructor call only
    assert ("x", 13) not in b  # field_expression field_identifier


def test_let_shadowing_is_a_new_symbol(tmp_path: Path):
    path = tmp_path / "s.rs"
    path.write_text("fn f() -> i32 {\n    let x = 1;\n    let x = x + 1;\n    x\n}\n", encoding="utf-8")
    from slop.ast import GRAMMARS_BY_ID
    from slop.ast.binding import bind
    from slop.ast.tree import AST
    grammar, content = GRAMMARS_BY_ID["rust"], path.read_bytes()
    xs = sorted((b for b in bind(AST.parse(path, grammar).root.raw, content, grammar).values() if b.text == "x"),
                key=lambda b: b.start)
    first, second = xs[0].start, xs[1].start
    # first let, second let, `x` in `x + 1` (the first let: not its own value), the final `x`
    assert [b.definition for b in xs] == [first, second, first, second]
