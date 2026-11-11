"""Name binding in C++: class members seen from in-class methods, lambdas, range-for.

Limit: a method defined outside its class (``void A::f() {...}``) cannot see the class scope
lexically, so a bare field name there is free.
"""
from __future__ import annotations

from slop.ast import GRAMMARS_BY_ID
from slop.ast.binding import SymbolKind, bind
from slop.ast.tree import AST

SOURCE = """\
int g;
class A {
public:
    int fld;
    int *ptr;
    int arr[3];
    static int cnt;
    int get() { return fld + helper(); }
    int shadow(int fld) { int h = fld; return h; }
    int local() { int ptr = 1; return ptr; }
    int helper() const { return later + cnt; }
    void bump(A &other, A *o2) { other.fld = 1; o2->fld = 2; this->fld = 3; fld++; }
    int lam(int k) {
        int base = k;
        auto f = [base, &k](int m) { int t = m + base + fld; return t + k; };
        return f(1);
    }
    void loops(std::vector<int> v) {
        for (auto &e : v) { e += fld; }
        for (int i = 0; i < 3; i++) { fld += i; }
        for (auto [p, q] : v) { use(p, q); }
    }
    int later;
};
void A::out() { fld = 1; }
namespace n { void f(int a) { int b = a; } }
void h(int a) {
    if (int c = a; c > 0) { use(c); }
    try { } catch (const std::exception &ex) { use(ex); }
    auto l = [z = a](int m) { return z + m; };
    std::cout << a;
}
"""


def _roles(tmp_path, source=SOURCE):
    path = tmp_path / "t.cpp"
    path.write_text(source)
    grammar = GRAMMARS_BY_ID["cpp"]
    content = path.read_bytes()
    found = bind(AST.parse(path, grammar).root.raw, content, grammar)
    return [(b.text, content[:b.start].count(b"\n") + 1, b) for b in found.values()]


def _all(tmp_path, name, line, source=SOURCE):
    return [b for text, ln, b in _roles(tmp_path, source) if text == name and ln == line]


def _at(tmp_path, name, line, source=SOURCE):
    hits = _all(tmp_path, name, line, source)
    assert hits, (name, line)
    return hits[-1]


def test_field_and_method_defined_in_class(tmp_path):
    for name, line, role in (("fld", 4, SymbolKind.FIELD), ("ptr", 5, SymbolKind.FIELD), ("arr", 6, SymbolKind.FIELD),
                             ("cnt", 7, SymbolKind.FIELD), ("get", 8, SymbolKind.METHOD),
                             ("helper", 11, SymbolKind.METHOD), ("later", 23, SymbolKind.FIELD)):
        b = _at(tmp_path, name, line)
        assert b.kind is role and b.defines, (name, line)


def test_bare_field_and_sibling_method_resolve_to_member(tmp_path):
    assert _at(tmp_path, "fld", 8).kind is SymbolKind.FIELD
    assert _at(tmp_path, "helper", 8).kind is SymbolKind.METHOD      # defined later in the class
    assert _at(tmp_path, "later", 11).kind is SymbolKind.FIELD       # field declared after the method
    assert _at(tmp_path, "cnt", 11).kind is SymbolKind.FIELD
    assert _at(tmp_path, "fld", 12).kind is SymbolKind.FIELD         # fld++


def test_parameter_and_local_shadow_field(tmp_path):
    assert [b.kind for b in _all(tmp_path, "fld", 9)] == [SymbolKind.PARAMETER, SymbolKind.PARAMETER]
    assert _at(tmp_path, "ptr", 10).kind is SymbolKind.LOCAL
    assert _at(tmp_path, "h", 9).kind is SymbolKind.LOCAL


def test_member_access_is_not_a_reference(tmp_path):
    assert _at(tmp_path, "other", 12).kind is SymbolKind.PARAMETER
    assert _at(tmp_path, "o2", 12).kind is SymbolKind.PARAMETER
    # `.fld`, `->fld`, `this->fld` are field_identifier nodes: only the bare `fld++` is a reference
    assert len(_all(tmp_path, "fld", 12)) == 1


def test_lambda_sees_enclosing_locals_and_fields(tmp_path):
    assert _at(tmp_path, "base", 15).kind is SymbolKind.LOCAL
    assert _at(tmp_path, "k", 15).kind is SymbolKind.PARAMETER
    assert _at(tmp_path, "m", 15).kind is SymbolKind.PARAMETER
    assert _at(tmp_path, "t", 15).kind is SymbolKind.LOCAL
    assert _at(tmp_path, "fld", 15).kind is SymbolKind.FIELD
    assert _at(tmp_path, "f", 16).kind is SymbolKind.LOCAL


def test_range_for_and_for_loops(tmp_path):
    assert _at(tmp_path, "e", 19).kind is SymbolKind.LOCAL
    assert _at(tmp_path, "v", 19).kind is SymbolKind.PARAMETER
    assert _at(tmp_path, "fld", 19).kind is SymbolKind.FIELD
    assert _at(tmp_path, "i", 20).kind is SymbolKind.LOCAL
    p = _all(tmp_path, "p", 21)
    assert [b.kind for b in p] == [SymbolKind.LOCAL, SymbolKind.LOCAL] and [b.defines for b in p] == [True, False]
    assert _all(tmp_path, "q", 21)[0].defines


def test_out_of_class_method_cannot_see_class_scope(tmp_path):
    assert _at(tmp_path, "fld", 25).kind is SymbolKind.FREE
    assert not _all(tmp_path, "out", 25)                       # qualified name: not a reference


def test_namespace_function(tmp_path):
    assert _at(tmp_path, "a", 26).kind is SymbolKind.PARAMETER
    assert _at(tmp_path, "b", 26).kind is SymbolKind.LOCAL


def test_condition_catch_and_init_capture(tmp_path):
    assert _at(tmp_path, "c", 28).kind is SymbolKind.LOCAL
    assert _at(tmp_path, "ex", 29).kind is SymbolKind.PARAMETER
    assert _at(tmp_path, "z", 30).kind is SymbolKind.LOCAL
    assert [b.kind for b in _all(tmp_path, "z", 30)] == [SymbolKind.LOCAL, SymbolKind.LOCAL]
    assert _at(tmp_path, "a", 31).kind is SymbolKind.PARAMETER
    assert not _all(tmp_path, "cout", 31)                       # qualified name: not a reference


def test_deep_declarators(tmp_path):
    src = "struct B { int **fp[2]; };\nint f(int **pp[2], int *&r) { int **p[2]; return **pp[0] + **p[0] + *r; }\n"
    assert _at(tmp_path, "fp", 1, src).kind is SymbolKind.FIELD
    assert _at(tmp_path, "pp", 2, src).kind is SymbolKind.PARAMETER
    assert _at(tmp_path, "r", 2, src).kind is SymbolKind.PARAMETER
    assert _at(tmp_path, "p", 2, src).kind is SymbolKind.LOCAL
