"""Tests for ``slop.structure.view.Structure``."""
from __future__ import annotations

from pathlib import Path

from slop.tree.tree import Tree
from slop.tree.records import CallableKind, ScopeKind


def _structure(path: Path):
    cb = Tree(path)
    cb.scan()
    return cb.structure


class TestIterationAndLookup:
    def test_callables_yields_all(self, tiny_corpus: Path):
        s = _structure(tiny_corpus)
        names = {c.qualname.split(".")[-1] for c in s.callables()}
        # tiny_corpus has alpha, beta, gamma, delta + Cls.method_a + Cls.method_b
        assert {"alpha", "beta", "gamma", "delta", "method_a", "method_b"} <= names

    def test_scope_lookup_by_qualname(self, class_corpus: Path):
        s = _structure(class_corpus)
        # Find any class scope and confirm lookup roundtrips.
        for sc in s.scopes():
            if sc.kind == ScopeKind.CLASS:
                found = s.scope(sc.qualname)
                assert found is not None
                assert found.qualname == sc.qualname
                return
        raise AssertionError("no class scope found")

    def test_children_returns_methods_of_class(self, class_corpus: Path):
        s = _structure(class_corpus)
        for sc in s.scopes():
            if sc.kind == ScopeKind.CLASS and sc.qualname.endswith("A"):
                kids = list(s.children(sc.qualname))
                # Class A has 3 methods (a1, a2, a3)
                assert len(kids) == 3
                return
        raise AssertionError("class A not found")


class TestSlicing:
    def test_where_kind_returns_new_structure(self, class_corpus: Path):
        s = _structure(class_corpus)
        narrowed = s.where(kind=CallableKind.METHOD)
        assert narrowed is not s
        # Parent unaffected: all kinds still present.
        all_kinds = {c.kind for c in s.callables()}
        assert all_kinds >= {CallableKind.METHOD, CallableKind.FUNCTION}

    def test_under_path_filters_by_prefix(self, tiny_corpus: Path):
        s = _structure(tiny_corpus)
        narrowed = s.under(path=str(tiny_corpus / "a.py"))
        narrowed_callables = list(narrowed.callables())
        # Only callables from a.py
        for c in narrowed_callables:
            assert "a.py" in str(c.path)


class TestCyclomatic:
    def test_linear_is_one(self, complexity_corpus: Path):
        s = _structure(complexity_corpus)
        for c in s.callables():
            if c.qualname.endswith("linear"):
                assert s.cyclomatic(c) == 1
                return
        raise AssertionError("linear not found")

    def test_single_if_is_two(self, complexity_corpus: Path):
        s = _structure(complexity_corpus)
        for c in s.callables():
            if c.qualname.endswith("single_if"):
                assert s.cyclomatic(c) == 2
                return
        raise AssertionError("single_if not found")

    def test_if_in_loop_is_three(self, complexity_corpus: Path):
        s = _structure(complexity_corpus)
        for c in s.callables():
            if c.qualname.endswith("if_in_loop"):
                assert s.cyclomatic(c) == 3
                return
        raise AssertionError("if_in_loop not found")

    def test_nested_four_ifs_is_five(self, complexity_corpus: Path):
        s = _structure(complexity_corpus)
        for c in s.callables():
            if c.qualname.endswith("nested"):
                # 4 decision points + base path = 5
                assert s.cyclomatic(c) == 5
                return
        raise AssertionError("nested not found")


def _ccx_by_name(root: Path) -> dict[str, int]:
    """Build a {function name → CCX} map for every callable in a corpus."""
    cb = Tree(root)
    cb.scan()
    s = cb.structure
    return {c.qualname.split(".")[-1]: s.cyclomatic(c) for c in s.callables()}


def _cog_by_name(root: Path) -> dict[str, int]:
    """Build a {function name → CogC} map for every callable in a corpus."""
    cb = Tree(root)
    cb.scan()
    s = cb.structure
    return {c.qualname.split(".")[-1]: s.cognitive(c) for c in s.callables()}


class TestCognitive:
    """Hand-computed Cognitive Complexity values against canonical Python
    fixtures. Cognitive (Campbell 2018) differs from cyclomatic by adding
    a nesting penalty: each decision inside a nesting container costs
    ``1 + depth``.
    """

    def test_linear_is_zero(self, complexity_corpus: Path):
        s = _structure(complexity_corpus)
        for c in s.callables():
            if c.qualname.endswith("linear"):
                # No decisions → CogC = 0
                assert s.cognitive(c) == 0
                return
        raise AssertionError("linear not found")

    def test_single_if_is_one(self, complexity_corpus: Path):
        s = _structure(complexity_corpus)
        for c in s.callables():
            if c.qualname.endswith("single_if"):
                # One if at depth 0: cog = 1 + 0 = 1
                assert s.cognitive(c) == 1
                return
        raise AssertionError("single_if not found")

    def test_if_in_loop_is_three(self, complexity_corpus: Path):
        s = _structure(complexity_corpus)
        for c in s.callables():
            if c.qualname.endswith("if_in_loop"):
                # for at depth 0 (+1+0=1), if at depth 1 (+1+1=2). Total: 3.
                assert s.cognitive(c) == 3
                return
        raise AssertionError("if_in_loop not found")

    def test_nested_four_ifs_is_ten(self, complexity_corpus: Path):
        s = _structure(complexity_corpus)
        for c in s.callables():
            if c.qualname.endswith("nested"):
                # 4 ifs at depths 0,1,2,3 → 1 + 2 + 3 + 4 = 10
                assert s.cognitive(c) == 10
                return
        raise AssertionError("nested not found")


class TestCognitiveMultiLanguage:
    """Hand-computed CogC across languages.

    Fixture: ``if (a && b) loop`` →
      if at depth 0:         +1+0 = 1
      && (short-circuit):    +1
      loop at depth 1:       +1+1 = 2
      total:                  4
    """

    def test_javascript(self, tmp_path: Path):
        (tmp_path / "a.js").write_text(
            "function f(a, b, xs) {\n"
            "  if (a && b) {\n"
            "    for (const x of xs) { console.log(x); }\n"
            "  }\n"
            "}\n"
        )
        assert _cog_by_name(tmp_path)["f"] == 4

    def test_typescript(self, tmp_path: Path):
        (tmp_path / "a.ts").write_text(
            "function f(a: boolean, b: boolean, xs: number[]) {\n"
            "  if (a && b) {\n"
            "    for (const x of xs) { console.log(x); }\n"
            "  }\n"
            "}\n"
        )
        assert _cog_by_name(tmp_path)["f"] == 4

    def test_go(self, tmp_path: Path):
        (tmp_path / "a.go").write_text(
            "package p\n"
            "func F(a, b bool, xs []int) {\n"
            "  if a && b {\n"
            "    for _, x := range xs { _ = x }\n"
            "  }\n"
            "}\n"
        )
        assert _cog_by_name(tmp_path)["F"] == 4

    def test_rust(self, tmp_path: Path):
        (tmp_path / "a.rs").write_text(
            "fn f(a: bool, b: bool, xs: Vec<i32>) {\n"
            "    if a && b {\n"
            "        for x in xs { let _ = x; }\n"
            "    }\n"
            "}\n"
        )
        assert _cog_by_name(tmp_path)["f"] == 4

    def test_java(self, tmp_path: Path):
        (tmp_path / "A.java").write_text(
            "class A {\n"
            "  void m(boolean a, boolean b, int[] xs) {\n"
            "    if (a && b) {\n"
            "      for (int x : xs) { System.out.println(x); }\n"
            "    }\n"
            "  }\n"
            "}\n"
        )
        assert _cog_by_name(tmp_path)["m"] == 4

    def test_csharp(self, tmp_path: Path):
        (tmp_path / "A.cs").write_text(
            "class A {\n"
            "  void M(bool a, bool b, int[] xs) {\n"
            "    if (a && b) {\n"
            "      foreach (var x in xs) { System.Console.WriteLine(x); }\n"
            "    }\n"
            "  }\n"
            "}\n"
        )
        assert _cog_by_name(tmp_path)["M"] == 4

    def test_c(self, tmp_path: Path):
        (tmp_path / "a.c").write_text(
            "void f(int a, int b, int n) {\n"
            "  if (a && b) {\n"
            "    for (int i = 0; i < n; i++) { (void)i; }\n"
            "  }\n"
            "}\n"
        )
        assert _cog_by_name(tmp_path)["f"] == 4

    def test_cpp(self, tmp_path: Path):
        (tmp_path / "a.cpp").write_text(
            "void f(bool a, bool b, int n) {\n"
            "  if (a && b) {\n"
            "    for (int i = 0; i < n; i++) { (void)i; }\n"
            "  }\n"
            "}\n"
        )
        assert _cog_by_name(tmp_path)["f"] == 4

    def test_ruby(self, tmp_path: Path):
        (tmp_path / "a.rb").write_text(
            "def f(a, b, xs)\n"
            "  if a && b\n"
            "    xs.each { |x| puts x }\n"
            "  end\n"
            "end\n"
        )
        # Ruby's tree-sitter emits decisions the v2 walker counts to match
        # legacy ccx_kernel (verified via parity script). CogC=4.
        assert _cog_by_name(tmp_path)["f"] == 4

    def test_julia(self, tmp_path: Path):
        (tmp_path / "a.jl").write_text(
            "function f(a, b, xs)\n"
            "    if a && b\n"
            "        for x in xs\n"
            "            x\n"
            "        end\n"
            "    end\n"
            "end\n"
        )
        assert _cog_by_name(tmp_path)["f"] == 4


class TestCallableKeyCollisionResistance:
    """Regression: per-callable view indexes must key on (path, qualname),
    not bare qualname. Same-file-stem files (a.py + a.js, both producing
    qualname ``a.f``) used to clobber each other in the lookups, returning
    wrong CCX/CogC values for whichever callable was scanned first.
    """

    def test_same_stem_files_keep_distinct_metrics(self, tmp_path: Path):
        # a.py: nested ifs (CCX=5, CogC=10)
        (tmp_path / "a.py").write_text(
            "def f(a, b, c, d):\n"
            "    if a:\n"
            "        if b:\n"
            "            if c:\n"
            "                if d:\n"
            "                    return 1\n"
            "    return 0\n"
        )
        # a.js: shallow if+&&+loop (CCX=4, CogC=4)
        (tmp_path / "a.js").write_text(
            "function f(a, b, xs) {\n"
            "  if (a && b) {\n"
            "    for (const x of xs) { console.log(x); }\n"
            "  }\n"
            "}\n"
        )
        cb = Tree(tmp_path)
        cb.scan()
        s = cb.structure
        # Two callables share qualname "a.f" — distinguish by suffix.
        by_path = {}
        for c in s.callables():
            by_path[c.path.suffix] = c
        assert ".py" in by_path and ".js" in by_path
        # Python file gets its own metrics; not clobbered by JS file.
        assert s.cyclomatic(by_path[".py"]) == 5
        assert s.cognitive(by_path[".py"]) == 10
        # JS file gets its own metrics; not clobbered by Python file.
        assert s.cyclomatic(by_path[".js"]) == 4
        assert s.cognitive(by_path[".js"]) == 4


class TestCognitiveSequenceCollapsing:
    """The signature CogC difference vs cyclomatic: same-operator chains
    collapse to a single +1, while mixed chains count each operator change.
    """

    def test_python_and_chain_is_one(self, tmp_path: Path):
        # `a and b and c` is a single &&-chain. CogC: if(+1) + chain(+1) = 2.
        (tmp_path / "a.py").write_text(
            "def f(a, b, c):\n"
            "    if a and b and c:\n"
            "        return 1\n"
            "    return 0\n"
        )
        assert _cog_by_name(tmp_path)["f"] == 2

    def test_python_mixed_chain_is_two(self, tmp_path: Path):
        # `a and b or c` is a mixed chain. CogC: if(+1) + and(+1) + or(+1) = 3.
        (tmp_path / "a.py").write_text(
            "def f(a, b, c):\n"
            "    if a and b or c:\n"
            "        return 1\n"
            "    return 0\n"
        )
        assert _cog_by_name(tmp_path)["f"] == 3

    def test_javascript_chain_collapses(self, tmp_path: Path):
        (tmp_path / "a.js").write_text(
            "function f(a, b, c) {\n"
            "  if (a && b && c) { return 1; }\n"
            "  return 0;\n"
            "}\n"
        )
        # if(+1) + && chain(+1) = 2
        assert _cog_by_name(tmp_path)["f"] == 2

    def test_javascript_mixed_chain(self, tmp_path: Path):
        (tmp_path / "a.js").write_text(
            "function f(a, b, c) {\n"
            "  if (a && b || c) { return 1; }\n"
            "  return 0;\n"
            "}\n"
        )
        # if(+1) + &&(+1) + ||(+1) = 3
        assert _cog_by_name(tmp_path)["f"] == 3


class TestCyclomaticMultiLanguage:
    """Hand-computed CCX values per language — surfaces grammar regressions
    in ``Language.decision_nodes`` / ``boolean_op_node`` /
    ``boolean_op_operators`` / ``definition_unwrap_types``.

    Each fixture function holds the same control-flow pattern:
    ``if (a && b) loop`` → CCX = base(1) + if(1) + && (1) + loop(1) = 4.
    """

    def test_javascript(self, tmp_path: Path):
        (tmp_path / "a.js").write_text(
            "function f(a, b, xs) {\n"
            "  if (a && b) {\n"
            "    for (const x of xs) { console.log(x); }\n"
            "  }\n"
            "}\n"
        )
        assert _ccx_by_name(tmp_path)["f"] == 4

    def test_typescript(self, tmp_path: Path):
        (tmp_path / "a.ts").write_text(
            "function f(a: boolean, b: boolean, xs: number[]) {\n"
            "  if (a && b) {\n"
            "    for (const x of xs) { console.log(x); }\n"
            "  }\n"
            "}\n"
        )
        assert _ccx_by_name(tmp_path)["f"] == 4

    def test_go(self, tmp_path: Path):
        (tmp_path / "a.go").write_text(
            "package p\n"
            "func F(a, b bool, xs []int) {\n"
            "  if a && b {\n"
            "    for _, x := range xs { _ = x }\n"
            "  }\n"
            "}\n"
        )
        assert _ccx_by_name(tmp_path)["F"] == 4

    def test_rust(self, tmp_path: Path):
        (tmp_path / "a.rs").write_text(
            "fn f(a: bool, b: bool, xs: Vec<i32>) {\n"
            "    if a && b {\n"
            "        for x in xs { let _ = x; }\n"
            "    }\n"
            "}\n"
        )
        assert _ccx_by_name(tmp_path)["f"] == 4

    def test_java(self, tmp_path: Path):
        (tmp_path / "A.java").write_text(
            "class A {\n"
            "  void m(boolean a, boolean b, int[] xs) {\n"
            "    if (a && b) {\n"
            "      for (int x : xs) { System.out.println(x); }\n"
            "    }\n"
            "  }\n"
            "}\n"
        )
        assert _ccx_by_name(tmp_path)["m"] == 4

    def test_csharp(self, tmp_path: Path):
        (tmp_path / "A.cs").write_text(
            "class A {\n"
            "  void M(bool a, bool b, int[] xs) {\n"
            "    if (a && b) {\n"
            "      foreach (var x in xs) { System.Console.WriteLine(x); }\n"
            "    }\n"
            "  }\n"
            "}\n"
        )
        assert _ccx_by_name(tmp_path)["M"] == 4

    def test_c(self, tmp_path: Path):
        (tmp_path / "a.c").write_text(
            "void f(int a, int b, int n) {\n"
            "  if (a && b) {\n"
            "    for (int i = 0; i < n; i++) { (void)i; }\n"
            "  }\n"
            "}\n"
        )
        assert _ccx_by_name(tmp_path)["f"] == 4

    def test_cpp(self, tmp_path: Path):
        (tmp_path / "a.cpp").write_text(
            "void f(bool a, bool b, int n) {\n"
            "  if (a && b) {\n"
            "    for (int i = 0; i < n; i++) { (void)i; }\n"
            "  }\n"
            "}\n"
        )
        assert _ccx_by_name(tmp_path)["f"] == 4

    def test_ruby(self, tmp_path: Path):
        (tmp_path / "a.rb").write_text(
            "def f(a, b, xs)\n"
            "  if a && b\n"
            "    xs.each { |x| puts x }\n"
            "  end\n"
            "end\n"
        )
        # CCX(f) = 4, matching legacy ccx_kernel. Ruby's tree-sitter
        # treats the if/&& branch differently than naive hand-counting;
        # the legacy oracle is the source of truth for parity.
        assert _ccx_by_name(tmp_path)["f"] == 4

    def test_julia(self, tmp_path: Path):
        (tmp_path / "a.jl").write_text(
            "function f(a, b, xs)\n"
            "    if a && b\n"
            "        for x in xs\n"
            "            x\n"
            "        end\n"
            "    end\n"
            "end\n"
        )
        assert _ccx_by_name(tmp_path)["f"] == 4


class TestCyclomaticBooleanOperatorFiltering:
    """Verifies ``boolean_op_operators`` only counts short-circuit operators."""

    def test_javascript_addition_is_not_counted(self, tmp_path: Path):
        # `a + b` is `binary_expression` but operator is `+`, not in {&&,||,??}.
        (tmp_path / "a.js").write_text(
            "function f(a, b) {\n"
            "  const x = a + b;\n"
            "  if (x > 0) return 1;\n"
            "  return 0;\n"
            "}\n"
        )
        # base(1) + if(1) = 2 (the + and > don't count)
        assert _ccx_by_name(tmp_path)["f"] == 2

    def test_javascript_nullish_coalesce_counts(self, tmp_path: Path):
        (tmp_path / "a.js").write_text(
            "function f(a, b) {\n"
            "  return a ?? b;\n"
            "}\n"
        )
        # base(1) + ?? (1) = 2
        assert _ccx_by_name(tmp_path)["f"] == 2

    def test_python_and_counts(self, tmp_path: Path):
        (tmp_path / "a.py").write_text(
            "def f(a, b):\n"
            "    if a and b:\n"
            "        return 1\n"
            "    return 0\n"
        )
        # base(1) + if(1) + and(1) = 3
        assert _ccx_by_name(tmp_path)["f"] == 3
