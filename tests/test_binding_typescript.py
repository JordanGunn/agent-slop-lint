"""Name binding for TypeScript: scoping, hoisting, destructuring, members."""
from __future__ import annotations

from slop.ast import GRAMMARS_BY_ID
from slop.ast.binding import SymbolKind, bind
from slop.ast.tree import AST

SOURCE = """\
const top = 1;
function f(p: number, {q, r: s}: Pair, [t, u = 2]: number[], ...rest: string[]): void {
  let loc: number = p + q;
  obj.prop = loc;
  this.x = s;
  const o = { key: loc, short, [t]: u };
  for (const item of rest) { use(item); }
  for (let i = 0; i < 3; i++) { use(i); }
  try { later(); } catch (err) { use(err); }
  const g = (x: number) => x + loc;
  { let loc = 2; use(loc); }
  early(top2);
  const top2 = 5;
  return later2();
  function later2() { return 1; }
}
class A extends B implements I {
  field: number = 1;
  constructor(public pub: number, priv?: string) { super(); }
  m(arg: T): U { return arg + this.field + field; }
}
const fe = function named(z: Z) { return named(z); };
import { imp as alias, plain } from "m";
export { top };
enum E { One }
interface I { name: string; go(n: number): void }
"""


def occurrences(tmp_path, source=SOURCE):
    path = tmp_path / "m.ts"
    path.write_text(source)
    grammar = GRAMMARS_BY_ID["typescript"]
    found = bind(AST.parse(path, grammar).root.raw, path.read_bytes(), grammar)
    lines = path.read_bytes()
    return [(b.text, lines[:b.start].count(b"\n") + 1, b) for b in sorted(found.values(), key=lambda b: b.start)]


def at(tmp_path, text, line, nth=0, source=SOURCE):
    return [b for t, n, b in occurrences(tmp_path, source) if t == text and n == line][nth]


def test_parameters_including_destructured(tmp_path):
    for name in ("p", "q", "s", "t", "u", "rest"):
        found = at(tmp_path, name, 2)
        assert (found.kind, found.defines) == (SymbolKind.PARAMETER, True), name
    assert at(tmp_path, "p", 3).kind is SymbolKind.PARAMETER
    assert at(tmp_path, "rest", 7).kind is SymbolKind.PARAMETER


def test_pair_pattern_key_is_not_a_name(tmp_path):
    assert [b for t, n, b in occurrences(tmp_path) if t == "r"] == []


def test_member_names_are_not_references(tmp_path):
    names = {(t, n) for t, n, _ in occurrences(tmp_path)}
    assert ("prop", 4) not in names and ("key", 6) not in names
    assert ("field", 20) in names           # only the bare one
    assert at(tmp_path, "obj", 4).kind is SymbolKind.FREE


def test_locals_and_shadowing(tmp_path):
    assert (at(tmp_path, "loc", 3).kind, at(tmp_path, "loc", 3).defines) == (SymbolKind.LOCAL, True)
    assert at(tmp_path, "loc", 4).definition == at(tmp_path, "loc", 3).start
    inner = at(tmp_path, "loc", 11, 0)
    assert inner.defines and inner.definition == inner.start
    use = at(tmp_path, "loc", 11, 1)
    assert use.definition == inner.start          # the block's loc hides the outer one
    assert at(tmp_path, "loc", 10).definition == at(tmp_path, "loc", 3).start


def test_type_positions_and_parameter_properties(tmp_path):
    names = {(t, n) for t, n, _ in occurrences(tmp_path)}
    assert not {("Pair", 2), ("Z", 22), ("I", 17), ("B", 17)} & names - {("B", 17)}
    pub = at(tmp_path, "pub", 19)
    assert (pub.kind, pub.defines) == (SymbolKind.PARAMETER, True)
    assert at(tmp_path, "priv", 19).kind is SymbolKind.PARAMETER
    assert at(tmp_path, "E", 25).defines


def test_object_literal(tmp_path):
    assert at(tmp_path, "loc", 6).kind is SymbolKind.LOCAL
    assert at(tmp_path, "short", 6).kind is SymbolKind.FREE
    assert at(tmp_path, "t", 6).kind is SymbolKind.PARAMETER


def test_loop_and_catch_variables(tmp_path):
    item = at(tmp_path, "item", 7, 0)
    assert item.defines and item.kind is SymbolKind.LOCAL
    assert at(tmp_path, "item", 7, 1).definition == item.start
    i = at(tmp_path, "i", 8, 0)
    assert all(b.definition == i.start for t, n, b in occurrences(tmp_path) if t == "i" and n == 8)
    err = at(tmp_path, "err", 9, 0)
    assert err.defines and at(tmp_path, "err", 9, 1).definition == err.start


def test_arrow_with_bare_parameter_closes_over_local(tmp_path):
    x = at(tmp_path, "x", 10, 0)
    assert (x.kind, x.defines) == (SymbolKind.PARAMETER, True)
    assert at(tmp_path, "x", 10, 1).definition == x.start
    assert at(tmp_path, "loc", 10).kind is SymbolKind.LOCAL


def test_bindings_are_hoisted(tmp_path):
    use = at(tmp_path, "top2", 12)
    assert use.kind is SymbolKind.LOCAL and use.definition == at(tmp_path, "top2", 13).start
    assert at(tmp_path, "later2", 14).definition == at(tmp_path, "later2", 15).start


def test_class_body_names_are_not_visible_to_methods(tmp_path):
    assert at(tmp_path, "field", 20).kind is SymbolKind.FREE
    assert at(tmp_path, "arg", 20, 1).kind is SymbolKind.PARAMETER
    assert (at(tmp_path, "A", 17).kind, at(tmp_path, "A", 17).defines) == (SymbolKind.LOCAL, True)


def test_named_function_expression_sees_its_own_name(tmp_path):
    named = at(tmp_path, "named", 22, 0)
    assert named.defines and at(tmp_path, "named", 22, 1).definition == named.start


def test_imports_and_exports(tmp_path):
    assert at(tmp_path, "alias", 23).defines
    assert [t for t, n, _ in occurrences(tmp_path) if n == 23 and t == "imp"] == []
    assert at(tmp_path, "plain", 23).defines
    assert at(tmp_path, "top", 24).definition == at(tmp_path, "top", 1).start


def test_nested_destructuring_declaration(tmp_path):
    source = "const { a: [b], m: { n = 1 }, ...d } = obj;\nuse(b, n, d);\n"
    for name in ("b", "n", "d"):
        assert at(tmp_path, name, 2, source=source).definition == at(tmp_path, name, 1, source=source).start


def test_class_fields_are_field_definitions(tmp_path):
    source = "class A {\n  f: number = 1;\n  m() { this.g = 1; other.h = 2; return this.f; }\n}\n"
    found = at(tmp_path, "f", 2, source=source)
    assert (found.kind, found.defines) == (SymbolKind.FIELD, True)
    assigned = at(tmp_path, "g", 3, source=source)
    assert (assigned.kind, assigned.defines) == (SymbolKind.FIELD, True)
    assert [t for t, n, _ in occurrences(tmp_path, source) if t == "h"] == []      # other.h is not ours


def test_a_member_assigned_through_this_anywhere_in_a_method_is_a_field(tmp_path):
    source = "class A { m() { if (c) { this.w = 1; } this.v = 2; this.u += 1; } }\n"
    names = {(t, n) for t, n, _ in occurrences(tmp_path, source)}
    assert at(tmp_path, "w", 1, source=source).kind is SymbolKind.FIELD      # inside a nested block
    assert at(tmp_path, "v", 1, source=source).kind is SymbolKind.FIELD
    assert ("u", 1) not in names                                       # an update declares nothing
