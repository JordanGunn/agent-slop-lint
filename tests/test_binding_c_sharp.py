"""Name binding in C#: what each identifier in a class body refers to."""
from __future__ import annotations

from slop.ast import GRAMMARS_BY_ID
from slop.ast.binding import SymbolKind, bind
from slop.ast.tree import AST

SOURCE = """\
class A : B {
    int count;
    public int Prop { get; set; }
    public A(int count, string s) { this.count = count; }
    int Run(int n) {
        int x = n + later;
        for (int i = 0; i < n; i++) { x += i; }
        foreach (var t in items) { Use(t); }
        foreach (var (k, v) in pairs) { Use(k); }
        try { Go(); } catch (IOException e) { Log(e); }
        Action r = () => count++;
        Func<int, int> f = a => a + x;
        Func<int, int, int> g = (p, q) => p + q;
        obj.count = other.Run(x);
        Helper(count); Prop = 3; this.Prop = 4;
        int count = 5;
        { int inner = 1; inner++; }
        inner = 2;
        using (var rd = Open()) { rd.Read(); }
        int.TryParse(str, out var parsed); Use(parsed);
        int Local(int w) => w + x;
        Local(1);
        if (o is Foo foo && foo.Ok()) { foo.Go(); }
        Call(name: 5);
        return Prop + count + A.K + obj?.Val;
    }
    void Helper(int v) { }
    int later;
}
"""


def roles(tmp_path):
    path = tmp_path / "A.cs"
    path.write_text(SOURCE)
    content = path.read_bytes()
    grammar = GRAMMARS_BY_ID["c_sharp"]
    found = bind(AST.parse(path, grammar).root.raw, content, grammar)
    by_name: dict[tuple[str, int], list] = {}
    for b in found.values():
        by_name.setdefault((b.text, content[:b.start].count(b"\n") + 1), []).append(b)
    return by_name


def role(by_name, text, line, nth=0):
    return by_name[(text, line)][nth].kind


def test_fields_properties_and_parameters(tmp_path):
    r = roles(tmp_path)
    assert role(r, "count", 2) is SymbolKind.FIELD
    assert role(r, "Prop", 3) is SymbolKind.FIELD               # a property is a member
    assert [b.kind for b in r[("count", 4)]] == [SymbolKind.PARAMETER, SymbolKind.PARAMETER]   # `this.count` is not a name
    assert role(r, "Prop", 15, 0) is SymbolKind.FIELD           # bare property use


def test_member_access_names_are_not_references(tmp_path):
    r = roles(tmp_path)
    assert ("count", 14) not in r and ("Run", 14) not in r        # obj.count, other.Run
    assert [b.text for b in r[("Prop", 15)]] == ["Prop"]  # `this.Prop` adds none
    assert ("K", 25) not in r and ("Val", 25) not in r and ("Ok", 23) not in r
    assert ("name", 24) not in r                           # a named argument
    assert ("Read", 19) not in r and ("TryParse", 20) not in r


def test_locals_loops_catch_and_lambdas(tmp_path):
    r = roles(tmp_path)
    assert role(r, "x", 6, 0) is SymbolKind.LOCAL and role(r, "n", 6) is SymbolKind.PARAMETER
    assert role(r, "i", 7, 0) is SymbolKind.LOCAL
    assert role(r, "t", 8, 0) is SymbolKind.LOCAL and role(r, "t", 8, 1) is SymbolKind.LOCAL
    assert role(r, "k", 9, 0) is SymbolKind.LOCAL and role(r, "v", 9, 0) is SymbolKind.LOCAL
    assert role(r, "k", 9, 1) is SymbolKind.LOCAL
    assert role(r, "e", 10, 0) is SymbolKind.PARAMETER and role(r, "e", 10, 1) is SymbolKind.PARAMETER
    assert role(r, "x", 12) is SymbolKind.LOCAL                  # a lambda reads an outer local
    assert role(r, "a", 12, 0) is SymbolKind.PARAMETER and role(r, "a", 12, 1) is SymbolKind.PARAMETER
    assert role(r, "p", 13, 1) is SymbolKind.PARAMETER and role(r, "q", 13, 1) is SymbolKind.PARAMETER


def test_members_before_declaration_and_shadowing(tmp_path):
    r = roles(tmp_path)
    assert role(r, "later", 6) is SymbolKind.FIELD              # field declared after the method
    assert role(r, "Helper", 15) is SymbolKind.METHOD            # bare sibling-method call
    assert role(r, "count", 11) is SymbolKind.FIELD             # before `int count` below
    assert role(r, "count", 15) is SymbolKind.FIELD
    assert role(r, "count", 16) is SymbolKind.LOCAL              # the declaration shadows the field
    assert role(r, "count", 25) is SymbolKind.LOCAL


def test_block_scope_using_out_var_patterns_and_local_functions(tmp_path):
    r = roles(tmp_path)
    assert role(r, "inner", 17, 1) is SymbolKind.LOCAL
    assert role(r, "inner", 18) is SymbolKind.FREE               # out of its block
    assert role(r, "rd", 19, 0) is SymbolKind.LOCAL and role(r, "rd", 19, 1) is SymbolKind.LOCAL
    assert role(r, "parsed", 20, 0) is SymbolKind.LOCAL and role(r, "parsed", 20, 1) is SymbolKind.LOCAL
    assert role(r, "Local", 21) is SymbolKind.LOCAL and role(r, "Local", 22) is SymbolKind.LOCAL
    assert role(r, "w", 21, 1) is SymbolKind.PARAMETER
    assert role(r, "x", 21) is SymbolKind.LOCAL
    assert all(b.kind is SymbolKind.LOCAL for b in r[("foo", 23)])
    assert role(r, "o", 23) is SymbolKind.FREE
