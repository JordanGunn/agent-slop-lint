"""Python name binding: function-wide (hoisted) locals, and methods that do not see their class body."""
from __future__ import annotations

from pathlib import Path

from slop.ast import GRAMMARS_BY_ID
from slop.ast.binding import SymbolKind, bind
from slop.ast.tree import AST

_SOURCE = """\
X = 1
class A:
    y = 2
    def f(self, p, *rest, k=3, **kw):
        q = p + X
        for i, j in rest:
            q += i
        g = lambda z: z + q
        [w for w in rest]
        print(late)
        late = 4
        self.v = y
        return f(k=1)
"""


def _roles(tmp_path: Path) -> dict[tuple[str, int], list[SymbolKind]]:
    path = tmp_path / "m.py"
    path.write_text(_SOURCE, encoding="utf-8")
    grammar, content = GRAMMARS_BY_ID["python"], path.read_bytes()
    found: dict[tuple[str, int], list[SymbolKind]] = {}
    for b in bind(AST.parse(path, grammar).root.raw, content, grammar).values():
        found.setdefault((b.text, content[:b.start].count(b"\n") + 1), []).append(b.kind)
    return found


def test_parameters_locals_and_closures_bind_lexically(tmp_path: Path):
    roles = _roles(tmp_path)
    assert roles[("p", 5)] == [SymbolKind.PARAMETER]
    assert roles[("X", 5)] == [SymbolKind.LOCAL]                  # module-level name
    assert roles[("i", 7)] == [SymbolKind.LOCAL]                  # loop variable
    assert roles[("q", 8)] == [SymbolKind.LOCAL]                  # a lambda reads the enclosing local
    assert roles[("z", 8)] == [SymbolKind.PARAMETER, SymbolKind.PARAMETER]


def test_a_name_is_local_to_its_whole_scope(tmp_path: Path):
    roles = _roles(tmp_path)
    assert roles[("w", 9)] == [SymbolKind.LOCAL, SymbolKind.LOCAL]      # used before its for-clause in the comprehension
    assert roles[("late", 10)] == [SymbolKind.LOCAL]              # assigned later in the function


def test_reassigning_a_name_is_one_variable_for_the_whole_scope(tmp_path: Path):
    path = tmp_path / "r.py"
    path.write_text("def f():\n    x = 1\n    x = x + 1\n    return x\n", encoding="utf-8")
    grammar, content = GRAMMARS_BY_ID["python"], path.read_bytes()
    found = bind(AST.parse(path, grammar).root.raw, content, grammar).values()
    xs = sorted((b for b in found if b.text == "x"), key=lambda b: b.start)
    assert {b.definition for b in xs} == {xs[0].start}      # every x is the first x


def test_a_method_does_not_see_its_class_body(tmp_path: Path):
    roles = _roles(tmp_path)
    assert roles[("y", 12)] == [SymbolKind.FREE]                  # class variable: only self.y reaches it
    assert roles[("f", 13)] == [SymbolKind.FREE]                  # sibling method: only self.f reaches it
    assert roles[("v", 12)] == [SymbolKind.FIELD]                 # self.v = ... declares a field of A
    assert ("k", 13) not in roles                           # a keyword name binds nothing


def test_fields_are_class_level_names_and_members_assigned_through_self(tmp_path: Path):
    path = tmp_path / "f.py"
    path.write_text("class A:\n    y = 2\n    def __init__(self, other):\n        self.a = 1\n"
                    "        self.b, self.c = 2, 3\n        other.z = 4\n        w = self.a\n", encoding="utf-8")
    grammar, content = GRAMMARS_BY_ID["python"], path.read_bytes()
    fields = [b.text for b in sorted(bind(AST.parse(path, grammar).root.raw, content, grammar).values(),
                                     key=lambda b: b.start) if b.kind is SymbolKind.FIELD and b.defines]
    assert fields == ["y", "a", "b", "c"]                   # not other.z, and self.a read is no definition
