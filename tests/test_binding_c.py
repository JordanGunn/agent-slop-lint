"""Name binding in C: parameters, block scope, ordered declarations, member access."""
from __future__ import annotations

from slop.ast import GRAMMARS_BY_ID
from slop.ast.binding import SymbolKind, bind
from slop.ast.tree import AST

SOURCE = """\
int g;
struct S { int fld; };
static int add(int a, char *b, int arr[], int (*fp)(int q)) {
    int x = a, *y = &x;
    int z;
    z = x + g;
    for (int i = 0; i < a; i++) {
        int x = i;
        z += x;
    }
    {
        int w = z;
        w++;
    }
    use(w);
    struct S s;
    s.fld = 1;
    struct S *p = &s;
    p->fld = 2;
    int late = early;
    int early = 3;
    return z + *y + b[0] + arr[0] + fp(1) + add(0, 0, 0, 0);
}
int other(void) { return add(1, 0, 0, 0) + g; }
"""


def _roles(tmp_path, source=SOURCE):
    path = tmp_path / "t.c"
    path.write_text(source)
    grammar = GRAMMARS_BY_ID["c"]
    content = path.read_bytes()
    found = bind(AST.parse(path, grammar).root.raw, content, grammar)
    return [(b.text, content[:b.start].count(b"\n") + 1, b) for b in found.values()]


def _at(tmp_path, name, line, source=SOURCE):
    hits = [b for text, ln, b in _roles(tmp_path, source) if text == name and ln == line]
    assert len(hits) >= 1, (name, line)
    return hits[-1] if len(hits) > 1 else hits[0]


def test_parameters_with_wrapping_declarators(tmp_path):
    for name in ("a", "b", "arr", "fp", "q"):
        assert _at(tmp_path, name, 3).kind is SymbolKind.PARAMETER
    assert _at(tmp_path, "b", 22).kind is SymbolKind.PARAMETER
    assert _at(tmp_path, "arr", 22).kind is SymbolKind.PARAMETER
    assert _at(tmp_path, "fp", 22).kind is SymbolKind.PARAMETER


def test_declarations_and_shadowing(tmp_path):
    assert _at(tmp_path, "y", 4).kind is SymbolKind.LOCAL and _at(tmp_path, "y", 4).defines
    assert _at(tmp_path, "z", 6).kind is SymbolKind.LOCAL
    inner = _at(tmp_path, "x", 9)
    outer = _at(tmp_path, "x", 6)
    assert inner.kind is SymbolKind.LOCAL and outer.kind is SymbolKind.LOCAL
    assert inner.definition != outer.definition


def test_for_init_and_block_scope(tmp_path):
    assert _at(tmp_path, "i", 8).kind is SymbolKind.LOCAL
    assert _at(tmp_path, "w", 13).kind is SymbolKind.LOCAL
    assert _at(tmp_path, "w", 15).kind is SymbolKind.FREE        # out of the block


def test_use_before_declaration_is_free(tmp_path):
    assert _at(tmp_path, "early", 20).kind is SymbolKind.FREE
    assert _at(tmp_path, "early", 21).defines


def test_member_access_is_not_a_reference(tmp_path):
    assert not [1 for text, ln, _ in _roles(tmp_path) if text == "fld" and ln in (17, 19)]
    assert _at(tmp_path, "s", 17).kind is SymbolKind.LOCAL
    assert _at(tmp_path, "p", 19).kind is SymbolKind.LOCAL


def test_functions_are_visible_to_later_functions(tmp_path):
    assert _at(tmp_path, "add", 24).kind is SymbolKind.LOCAL
    assert _at(tmp_path, "add", 22).kind is SymbolKind.LOCAL     # recursion
    assert _at(tmp_path, "use", 15).kind is SymbolKind.FREE


def test_macros_and_enumerators(tmp_path):
    src = "#define N 3\n#define SQ(x) ((x) * (x))\nenum C { RED };\nint f(int k) { int a[N]; return SQ(k) + RED; }\n"
    assert _at(tmp_path, "N", 4, src).kind is SymbolKind.LOCAL
    assert _at(tmp_path, "x", 2, src).kind is SymbolKind.PARAMETER
    assert _at(tmp_path, "RED", 4, src).kind is SymbolKind.LOCAL
    assert _at(tmp_path, "k", 4, src).kind is SymbolKind.PARAMETER


def test_struct_field_declaration_is_a_field(tmp_path):
    b = _at(tmp_path, "fld", 2)
    assert b.kind is SymbolKind.FIELD and b.defines


def test_deep_declarators(tmp_path):
    src = "int f(int **pp[2], char ***q) { int **p[2]; return **pp[0] + ***q + **p[0]; }\n"
    for name in ("pp", "q"):
        assert _at(tmp_path, name, 1, src).kind is SymbolKind.PARAMETER
    assert _at(tmp_path, "p", 1, src).kind is SymbolKind.LOCAL
