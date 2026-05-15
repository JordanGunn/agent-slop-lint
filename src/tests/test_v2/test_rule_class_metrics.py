"""Tests for the v2 CK class metrics (Chidamber & Kemerer 1994).

  structural.class.complexity              — WMC > threshold
  structural.class.coupling                — CBO > threshold
  structural.class.inheritance.depth       — DIT > threshold
  structural.class.inheritance.children    — NOC > threshold

The rules share a per-corpus inheritance index (parent_map +
children_map + known set), built once across structure.classes().
Verified against legacy ck_kernel on hand-computed fixtures for
Python / Java / Ruby; Go (receiver-based) and Rust (impl-based)
contribute 0 to all four — their pseudo-class story is a follow-up.
"""
from __future__ import annotations

from pathlib import Path

from slop.config.models import RuleConfig, SlopConfig
from slop.structure.rules.class_metrics import (
    run_coupling,
    run_inheritance_children,
    run_inheritance_depth,
    run_weighted,
)
from slop.tree.tree import Tree


def _rc(threshold: int) -> RuleConfig:
    return RuleConfig(enabled=True, severity="error", params={"threshold": threshold})


def _sc(tmp_path: Path) -> SlopConfig:
    return SlopConfig(root=str(tmp_path))


def _structure(tmp_path: Path):
    cb = Tree(tmp_path)
    cb.scan()
    return cb.structure


class TestWMC:
    def test_class_with_no_methods_has_wmc_zero(self, tmp_path: Path):
        (tmp_path / "a.py").write_text("class A:\n    pass\n")
        result = run_weighted(_structure(tmp_path), _rc(0), _sc(tmp_path))
        assert result.status == "pass"

    def test_class_method_ccx_sums(self, tmp_path: Path):
        (tmp_path / "a.py").write_text(
            "class A:\n"
            "    def linear(self):\n"
            "        return 1\n"            # ccx 1
            "    def branchy(self, x):\n"
            "        if x: return 1\n"      # ccx 2
            "        return 0\n"
            "    def nested(self, a, b):\n" # ccx 3 (2 ifs + base)
            "        if a:\n"
            "            if b:\n"
            "                return 1\n"
            "        return 0\n"
        )
        # WMC = 1 + 2 + 3 = 6. Threshold 5 → fail with WMC=6.
        result = run_weighted(_structure(tmp_path), _rc(5), _sc(tmp_path))
        assert result.status == "fail"
        assert result.violations[0].symbol == "A"
        assert result.violations[0].value == 6


class TestCBO:
    def test_cbo_counts_distinct_known_class_refs(self, tmp_path: Path):
        (tmp_path / "a.py").write_text(
            "class Pet: pass\n"
            "class Trainer: pass\n"
            "class Habitat: pass\n"
            "class Animal:\n"
            "    def setup(self):\n"
            "        self.pet = Pet()\n"
            "        self.trainer = Trainer()\n"
            "        self.habitat = Habitat()\n"
        )
        # Animal refs Pet, Trainer, Habitat → CBO = 3.
        result = run_coupling(_structure(tmp_path), _rc(2), _sc(tmp_path))
        animal = next(v for v in result.violations if v.symbol == "Animal")
        assert animal.value == 3

    def test_cbo_excludes_self_reference(self, tmp_path: Path):
        (tmp_path / "a.py").write_text(
            "class A:\n"
            "    def make(self):\n"
            "        return A()\n"
        )
        result = run_coupling(_structure(tmp_path), _rc(0), _sc(tmp_path))
        # A references only itself → CBO = 0.
        assert result.status == "pass"

    def test_cbo_ignores_unknown_class_names(self, tmp_path: Path):
        (tmp_path / "a.py").write_text(
            "class Foo:\n"
            "    def m(self):\n"
            "        # External, not declared in corpus → not counted.\n"
            "        return ExternalLib.Stuff()\n"
        )
        result = run_coupling(_structure(tmp_path), _rc(0), _sc(tmp_path))
        # No known classes outside Foo → CBO = 0.
        assert result.status == "pass"


class TestDIT:
    def test_dit_walks_inheritance_chain(self, tmp_path: Path):
        (tmp_path / "a.py").write_text(
            "class A: pass\n"
            "class B(A): pass\n"
            "class C(B): pass\n"
            "class D(C): pass\n"
        )
        result = run_inheritance_depth(_structure(tmp_path), _rc(2), _sc(tmp_path))
        # D's chain: D → C → B → A → 3 levels above D. DIT = 3.
        flagged = {v.symbol: v.value for v in result.violations}
        assert flagged.get("D") == 3

    def test_dit_zero_for_root_class(self, tmp_path: Path):
        (tmp_path / "a.py").write_text(
            "class Root: pass\n"
        )
        result = run_inheritance_depth(_structure(tmp_path), _rc(0), _sc(tmp_path))
        # Root has no parents → DIT = 0, threshold = 0, NOT > 0.
        assert result.status == "pass"

    def test_dit_handles_external_parents(self, tmp_path: Path):
        # External parent (not in corpus) doesn't add to DIT.
        (tmp_path / "a.py").write_text(
            "class A(ExternalBase): pass\n"
        )
        result = run_inheritance_depth(_structure(tmp_path), _rc(0), _sc(tmp_path))
        # ExternalBase isn't in known classes → DIT(A) = 0.
        assert result.status == "pass"


class TestNOC:
    def test_noc_counts_direct_subclasses(self, tmp_path: Path):
        (tmp_path / "a.py").write_text(
            "class Base: pass\n"
            "class A(Base): pass\n"
            "class B(Base): pass\n"
            "class C(Base): pass\n"
            "class D(Base): pass\n"
            "class E(Base): pass\n"
        )
        # Base has 5 direct subclasses.
        result = run_inheritance_children(_structure(tmp_path), _rc(3), _sc(tmp_path))
        flagged = {v.symbol: v.value for v in result.violations}
        assert flagged.get("Base") == 5

    def test_noc_counts_only_direct_children(self, tmp_path: Path):
        (tmp_path / "a.py").write_text(
            "class A: pass\n"
            "class B(A): pass\n"
            "class C(B): pass\n"  # C inherits B, not A directly
        )
        # A has 1 direct child (B); C is a grandchild, not a child.
        result = run_inheritance_children(_structure(tmp_path), _rc(0), _sc(tmp_path))
        flagged = {v.symbol: v.value for v in result.violations}
        assert flagged.get("A") == 1
        assert flagged.get("B") == 1


class TestMultiLanguage:
    """Same canonical 4-level inheritance shape in Python / Java / Ruby."""

    def test_python(self, tmp_path: Path):
        (tmp_path / "h.py").write_text(
            "class A: pass\n"
            "class B(A): pass\n"
            "class C(B): pass\n"
            "class D(C): pass\n"
        )
        result = run_inheritance_depth(_structure(tmp_path), _rc(0), _sc(tmp_path))
        d = next(v for v in result.violations if v.symbol == "D")
        assert d.value == 3

    def test_java(self, tmp_path: Path):
        (tmp_path / "H.java").write_text(
            "class A {}\n"
            "class B extends A {}\n"
            "class C extends B {}\n"
            "class D extends C {}\n"
        )
        result = run_inheritance_depth(_structure(tmp_path), _rc(0), _sc(tmp_path))
        d = next(v for v in result.violations if v.symbol == "D")
        assert d.value == 3

    def test_ruby(self, tmp_path: Path):
        (tmp_path / "h.rb").write_text(
            "class A; end\n"
            "class B < A; end\n"
            "class C < B; end\n"
            "class D < C; end\n"
        )
        result = run_inheritance_depth(_structure(tmp_path), _rc(0), _sc(tmp_path))
        d = next(v for v in result.violations if v.symbol == "D")
        assert d.value == 3

    def test_cpp(self, tmp_path: Path):
        (tmp_path / "h.hpp").write_text(
            "class A {};\n"
            "class B : public A {};\n"
            "class C : public B {};\n"
            "class D : public C {};\n"
        )
        result = run_inheritance_depth(_structure(tmp_path), _rc(0), _sc(tmp_path))
        d = next(v for v in result.violations if v.symbol == "D")
        assert d.value == 3


class TestGoReceiverLinking:
    """Go's ``func (s S) M() {}`` methods should be parented to S
    (their receiver struct), not to the file scope.
    """

    def test_struct_with_three_methods_wmc(self, tmp_path: Path):
        (tmp_path / "a.go").write_text(
            "package p\n"
            "type Animal struct { name string }\n"
            "func (a Animal) Speak() { if a.name == \"\" { return } }\n"   # ccx 2
            "func (a Animal) Walk() { for i := 0; i < 4; i++ { _ = i } }\n"  # ccx 2
            "func (a *Animal) Run() { if a == nil { return } }\n"            # ccx 2
        )
        result = run_weighted(_structure(tmp_path), _rc(0), _sc(tmp_path))
        animal = next(v for v in result.violations if v.symbol == "Animal")
        assert animal.value == 6  # 2 + 2 + 2

    def test_pointer_receiver_strips_pointer(self, tmp_path: Path):
        (tmp_path / "a.go").write_text(
            "package p\n"
            "type S struct {}\n"
            "func (s *S) M() {}\n"  # pointer receiver
        )
        # The method should attach to S, not *S.
        cb = Tree(tmp_path); cb.scan()
        methods = [c for c in cb.structure.callables() if c.qualname.endswith(".M")]
        assert len(methods) == 1
        assert methods[0].parent == "a.S"


class TestRustImplLinking:
    """Rust's ``impl S { fn m() {} }`` methods should be parented to S,
    not to the impl_item scope (which the generic walker emits as anonymous).
    """

    def test_struct_impl_methods_wmc(self, tmp_path: Path):
        (tmp_path / "a.rs").write_text(
            "struct Animal { name: String }\n"
            "impl Animal {\n"
            "    fn speak(&self) {\n"
            "        if self.name.is_empty() { return; }\n"      # ccx 2
            "    }\n"
            "    fn walk(&self) {\n"
            "        for i in 0..4 { let _ = i; }\n"              # ccx 2
            "    }\n"
            "    fn run(&self) {\n"
            "        if true { return; }\n"                       # ccx 2
            "    }\n"
            "}\n"
        )
        result = run_weighted(_structure(tmp_path), _rc(0), _sc(tmp_path))
        animal = next(v for v in result.violations if v.symbol == "Animal")
        assert animal.value == 6

    def test_methods_correctly_parented(self, tmp_path: Path):
        (tmp_path / "a.rs").write_text(
            "struct S {}\n"
            "impl S { fn m(&self) {} }\n"
        )
        cb = Tree(tmp_path); cb.scan()
        methods = [c for c in cb.structure.callables() if c.qualname.endswith(".m")]
        assert len(methods) == 1
        assert methods[0].parent == "a.S"

    def test_trait_impl_methods_parent_to_target(self, tmp_path: Path):
        # `impl Trait for S { fn m() {} }` — m should parent to S (the target).
        (tmp_path / "a.rs").write_text(
            "trait Speakable { fn speak(&self); }\n"
            "struct Dog {}\n"
            "impl Speakable for Dog {\n"
            "    fn speak(&self) { return; }\n"
            "}\n"
        )
        cb = Tree(tmp_path); cb.scan()
        speak = next(c for c in cb.structure.callables() if c.qualname.endswith(".speak"))
        assert speak.parent == "a.Dog"


class TestRubyOpenClassAggregation:
    """Ruby allows ``class Foo`` to be re-opened across multiple files.
    CK metrics aggregate across openings (legacy
    ``_aggregate_ruby_open_classes`` policy: sum WMC, max CBO/DIT/NOC).
    """

    def test_wmc_sums_across_openings(self, tmp_path: Path):
        (tmp_path / "a.rb").write_text(
            "class Animal\n"
            "  def speak\n"            # ccx 1
            "    raise NotImplementedError\n"
            "  end\n"
            "  def legs(custom)\n"     # ccx 2 (one if)
            "    if custom\n"
            "      4\n"
            "    else\n"
            "      0\n"
            "    end\n"
            "  end\n"
            "end\n"
        )
        (tmp_path / "b.rb").write_text(
            "class Animal\n"
            "  def lifespan(young)\n"  # ccx 2 (one if)
            "    if young\n"
            "      10\n"
            "    else\n"
            "      20\n"
            "    end\n"
            "  end\n"
            "end\n"
        )
        # Aggregated WMC = 1 + 2 + 2 = 5. Threshold 4 → fail.
        result = run_weighted(_structure(tmp_path), _rc(4), _sc(tmp_path))
        flagged = [v for v in result.violations if v.symbol == "Animal"]
        # ONE entry, not two — aggregation merged them.
        assert len(flagged) == 1
        assert flagged[0].value >= 5

    def test_no_aggregation_for_non_ruby(self, tmp_path: Path):
        # Same simple name across two Python files should NOT aggregate;
        # they're conceptually separate classes that happen to share a
        # name. Python doesn't have open-class semantics.
        (tmp_path / "a.py").write_text(
            "class Animal:\n"
            "    def m(self):\n"
            "        if True: return 1\n"
            "        return 0\n"
        )
        (tmp_path / "b.py").write_text(
            "class Animal:\n"
            "    def n(self):\n"
            "        if True: return 1\n"
            "        return 0\n"
        )
        # If aggregated: WMC = 2 + 2 = 4 → fail at threshold 3.
        # If NOT aggregated: WMC = 2 each → pass at threshold 3.
        result = run_weighted(_structure(tmp_path), _rc(3), _sc(tmp_path))
        flagged = [v for v in result.violations if v.symbol == "Animal"]
        assert len(flagged) == 0  # both pass independently
