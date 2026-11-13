"""Name binding in Java: what each identifier in a class body refers to."""
from __future__ import annotations

from slop.ast import GRAMMARS_BY_ID
from slop.ast.binding import SymbolKind, bind
from slop.ast.tree import AST

SOURCE = """\
class A extends B {
    int count;
    static final int K = 1, J = 2;
    A(int count, String s) { this.count = count; }
    int run(int n) {
        int x = n + later;
        for (int i = 0; i < n; i++) { x += i; }
        for (String t : items) { use(t); }
        try { go(); } catch (IOException e) { log(e); }
        Runnable r = () -> count++;
        Function<Integer, Integer> f = (a) -> a + x;
        BiFunction<Integer, Integer, Integer> g = (p, q) -> p + q;
        Function<Integer, Integer> h = z -> z;
        obj.count = other.run(x);
        helper(count);
        int count = 5;
        { int inner = 1; inner++; }
        inner = 2;
        if (o instanceof Foo foo && foo.ok()) { foo.go(); }
        this.helper(x);
        return A.K + count;
    }
    void helper(int v) { }
    int later;
    record P(int a, int b) { int sum() { return a + b; } }
    void anon() { new Thread(new Runnable() { int w; public void run() { w++; count++; } }); }
}
"""


def roles(tmp_path):
    path = tmp_path / "A.java"
    path.write_text(SOURCE)
    content = path.read_bytes()
    grammar = GRAMMARS_BY_ID["java"]
    found = bind(AST.parse(path, grammar).root.raw, content, grammar)
    by_name: dict[tuple[str, int], list] = {}
    for b in found.values():
        by_name.setdefault((b.text, content[:b.start].count(b"\n") + 1), []).append(b)
    return by_name


def role(by_name, text, line, nth=0):
    return by_name[(text, line)][nth].kind


def test_field_and_parameter(tmp_path):
    r = roles(tmp_path)
    assert role(r, "count", 2) is SymbolKind.FIELD
    assert role(r, "count", 4, 0) is SymbolKind.PARAMETER     # the parameter declaration
    assert [b.kind for b in r[("count", 4)]] == [SymbolKind.PARAMETER, SymbolKind.PARAMETER]  # `this.count` is not a name
    assert role(r, "K", 3) is SymbolKind.FIELD and role(r, "J", 3) is SymbolKind.FIELD


def test_this_field_and_receiver_members_are_not_references(tmp_path):
    r = roles(tmp_path)
    assert len(r[("count", 4)]) == 2                      # declaration + the bare right-hand side
    assert ("count", 14) not in r                         # obj.count
    assert ("run", 14) not in r                           # other.run(x)
    assert ("helper", 20) not in r                        # this.helper(x)
    assert ("K", 21) not in r                             # A.K


def test_locals_loops_catch_and_lambdas(tmp_path):
    r = roles(tmp_path)
    assert role(r, "x", 6) is SymbolKind.LOCAL and role(r, "n", 6) is SymbolKind.PARAMETER
    assert role(r, "i", 7, 0) is SymbolKind.LOCAL
    assert role(r, "t", 8, 0) is SymbolKind.LOCAL and role(r, "t", 8, 1) is SymbolKind.LOCAL
    assert role(r, "e", 9, 0) is SymbolKind.PARAMETER and role(r, "e", 9, 1) is SymbolKind.PARAMETER
    assert role(r, "x", 11) is SymbolKind.LOCAL                  # a lambda reads an outer local
    assert role(r, "a", 11, 1) is SymbolKind.PARAMETER
    assert role(r, "p", 12, 1) is SymbolKind.PARAMETER and role(r, "q", 12, 1) is SymbolKind.PARAMETER
    assert role(r, "z", 13, 1) is SymbolKind.PARAMETER


def test_members_before_declaration_and_shadowing(tmp_path):
    r = roles(tmp_path)
    assert role(r, "later", 6) is SymbolKind.FIELD             # field declared after the method
    assert role(r, "helper", 15) is SymbolKind.METHOD           # bare sibling-method call
    assert role(r, "count", 10) is SymbolKind.FIELD            # before `int count` below
    assert role(r, "count", 15) is SymbolKind.FIELD
    assert role(r, "count", 16) is SymbolKind.LOCAL             # the declaration shadows the field
    assert role(r, "count", 21) is SymbolKind.LOCAL             # and hides it afterwards


def test_block_scope_and_patterns(tmp_path):
    r = roles(tmp_path)
    assert role(r, "inner", 17, 1) is SymbolKind.LOCAL
    assert role(r, "inner", 18) is SymbolKind.FREE              # out of its block
    assert role(r, "foo", 19, 0) is SymbolKind.LOCAL
    assert all(b.kind is SymbolKind.LOCAL for b in r[("foo", 19)])
    assert role(r, "o", 19) is SymbolKind.FREE


def test_record_components_and_anonymous_class(tmp_path):  # slop: ignore[preferred-term]  Java's record components, not slop's scopes
    r = roles(tmp_path)
    assert role(r, "a", 25, 0) is SymbolKind.FIELD              # a record component is a member
    assert role(r, "a", 25, 1) is SymbolKind.FIELD
    assert role(r, "w", 26, 0) is SymbolKind.FIELD
    assert role(r, "count", 26) is SymbolKind.FIELD             # the anonymous class sees the outer field
