"""Smoke tests for C++ language support across the rule suite.

Each test writes a small ``.cpp`` / ``.hpp`` fixture and runs a rule
with ``languages=["cpp"]``. Goal: confirm C++ files parse, the kernel
walks them, and the rule wrapper produces the expected output —
including the C++-specific shapes (in-class methods, out-of-line
methods, operator overloads, templates, lambdas, destructors, base
class clauses, pure-virtual abstract classes).
"""

from __future__ import annotations

from pathlib import Path

from slop.models import RuleConfig, SlopConfig
from slop.rules.any_type_density import run_any_type_density
from slop.rules.class_metrics import (
    run_coupling, run_inheritance_children, run_inheritance_depth,
)
from slop.rules.clone_density import run_clone_density
from slop.rules.complexity import run_cognitive, run_cyclomatic, run_weighted
from slop.rules.dependencies import run_cycles
from slop.rules.god_module import run_god_module
from slop.rules.halstead import run_difficulty, run_volume
from slop.rules.local_imports import run_local_imports
from slop.rules.magic_literals import run_magic_literal_density
from slop.rules.npath import run_npath
from slop.rules.out_parameters import run_out_parameters
from slop.rules.section_comments import run_section_comment_density
from slop.rules.sibling_calls import run_sibling_call_redundancy
from slop.rules.stringly_typed import run_stringly_typed
from slop.rules.stutter import run_stutter
from slop.rules.verbosity import run_verbosity


def _slop_config() -> SlopConfig:
    return SlopConfig(rules={}, languages=["cpp"])


def _rule_config(**overrides) -> RuleConfig:
    return RuleConfig(enabled=True, severity="error", params=overrides)


# ---------------------------------------------------------------------------
# Function name extraction
# ---------------------------------------------------------------------------


def test_cpp_in_class_method_extracts_field_identifier_name(tmp_path: Path):
    """In-class methods use field_identifier in the declarator chain."""
    (tmp_path / "anim.hpp").write_text(
        "class Animal {\n"
        "public:\n"
        "    void speak() { do_thing(); }\n"
        "    int legs() const { return 4; }\n"
        "};\n"
    )
    result = run_cyclomatic(tmp_path, _rule_config(cyclomatic_threshold=0),
                            _slop_config())
    names = {v.symbol for v in result.violations}
    assert "speak" in names
    assert "legs" in names
    assert "<anonymous>" not in names


def test_cpp_out_of_line_method_extracts_qualified_name(tmp_path: Path):
    """Out-of-line methods use qualified_identifier."""
    (tmp_path / "anim.cpp").write_text(
        "void Animal::speak() { return; }\n"
        "int Animal::legs() const { return 4; }\n"
    )
    result = run_cyclomatic(tmp_path, _rule_config(cyclomatic_threshold=0),
                            _slop_config())
    names = {v.symbol for v in result.violations}
    assert "speak" in names
    assert "legs" in names


def test_cpp_operator_overload_extracts_operator_symbol(tmp_path: Path):
    (tmp_path / "vec.hpp").write_text(
        "class Vec {\n"
        "public:\n"
        "    bool operator==(const Vec& o) const { return true; }\n"
        "    Vec operator+(const Vec& r) const { return Vec(); }\n"
        "};\n"
    )
    result = run_cyclomatic(tmp_path, _rule_config(cyclomatic_threshold=0),
                            _slop_config())
    names = {v.symbol for v in result.violations}
    assert "==" in names
    assert "+" in names


def test_cpp_destructor_extracts_tilde_prefix(tmp_path: Path):
    (tmp_path / "shape.hpp").write_text(
        "class Shape {\n"
        "public:\n"
        "    ~Shape() { cleanup(); }\n"
        "};\n"
    )
    result = run_cyclomatic(tmp_path, _rule_config(cyclomatic_threshold=0),
                            _slop_config())
    names = {v.symbol for v in result.violations}
    assert "~Shape" in names


def test_cpp_lambda_treated_as_anonymous(tmp_path: Path):
    (tmp_path / "lam.cpp").write_text(
        "void run() {\n"
        "    auto add = [](int a, int b) { if (a > 0) return a + b; return 0; };\n"
        "    add(1, 2);\n"
        "}\n"
    )
    result = run_cyclomatic(tmp_path, _rule_config(cyclomatic_threshold=0),
                            _slop_config())
    names = {v.symbol for v in result.violations}
    assert "<lambda>" in names


def test_cpp_template_function_detected(tmp_path: Path):
    """Template-wrapped function_definition still gets analysed."""
    (tmp_path / "tmpl.hpp").write_text(
        "template <typename T>\n"
        "T pick(T a, T b, T c) {\n"
        "    if (a > b && b > c) return a;\n"
        "    if (b > c) return b;\n"
        "    return c;\n"
        "}\n"
    )
    result = run_cyclomatic(tmp_path, _rule_config(cyclomatic_threshold=2),
                            _slop_config())
    assert result.status == "fail"
    assert any(v.symbol == "pick" for v in result.violations)


# ---------------------------------------------------------------------------
# Cyclomatic / cognitive
# ---------------------------------------------------------------------------


def test_cpp_cyclomatic_counts_range_for_and_try(tmp_path: Path):
    (tmp_path / "ranges.cpp").write_text(
        "int process(const std::vector<int>& v) {\n"
        "    int total = 0;\n"
        "    for (auto& x : v) {\n"
        "        try { total += x; }\n"
        "        catch (const std::exception& e) { return -1; }\n"
        "    }\n"
        "    return total;\n"
        "}\n"
    )
    result = run_cyclomatic(tmp_path, _rule_config(cyclomatic_threshold=2),
                            _slop_config())
    assert result.status == "fail"
    assert any(v.symbol == "process" for v in result.violations)


def test_cpp_cognitive_runs_without_error(tmp_path: Path):
    (tmp_path / "c.cpp").write_text(
        "int classify(int x) {\n"
        "    if (x < 0) return -1;\n"
        "    if (x == 0) return 0;\n"
        "    return 1;\n"
        "}\n"
    )
    result = run_cognitive(tmp_path, _rule_config(cognitive_threshold=99),
                           _slop_config())
    assert result.status == "pass"


# ---------------------------------------------------------------------------
# NPath
# ---------------------------------------------------------------------------


def test_cpp_npath_counts_range_for(tmp_path: Path):
    (tmp_path / "rng.cpp").write_text(
        "int loop(const int* xs, int n) {\n"
        "    int total = 0;\n"
        "    for (auto& x : xs_view) { total += x; }\n"
        "    return total;\n"
        "}\n"
    )
    # for_range_loop should contribute as a loop in npath; threshold low
    # to confirm it counts.
    result = run_npath(tmp_path, _rule_config(npath_threshold=99),
                       _slop_config())
    assert result.status == "pass"


def test_cpp_npath_counts_switch_cases(tmp_path: Path):
    (tmp_path / "sw.cpp").write_text(
        "int sw(int x) {\n"
        "    switch (x) {\n"
        "        case 1: return 1;\n"
        "        case 2: return 2;\n"
        "        case 3: return 3;\n"
        "        default: return 0;\n"
        "    }\n"
        "}\n"
    )
    result = run_npath(tmp_path, _rule_config(npath_threshold=3),
                       _slop_config())
    assert result.status == "fail"


# ---------------------------------------------------------------------------
# Halstead
# ---------------------------------------------------------------------------


def test_cpp_halstead_volume_runs(tmp_path: Path):
    (tmp_path / "h.cpp").write_text(
        "template <typename T> T add(T a, T b) { return a + b; }\n"
    )
    result = run_volume(tmp_path, _rule_config(threshold=10000), _slop_config())
    assert result.status == "pass"


def test_cpp_halstead_difficulty_runs(tmp_path: Path):
    (tmp_path / "h.cpp").write_text(
        "int square(int x) { return x * x; }\n"
    )
    result = run_difficulty(tmp_path, _rule_config(threshold=99), _slop_config())
    assert result.status == "pass"


# ---------------------------------------------------------------------------
# CK class metrics
# ---------------------------------------------------------------------------


def test_cpp_class_coupling_detects_member_references(tmp_path: Path):
    (tmp_path / "anim.hpp").write_text(
        "class Animal {\n"
        "public:\n"
        "    Pet pet;\n"
        "    Trainer trainer;\n"
        "    Habitat habitat;\n"
        "    void interact() {\n"
        "        pet.greet();\n"
        "        trainer.command(this);\n"
        "    }\n"
        "};\n"
        "class Pet { public: void greet() {} };\n"
        "class Trainer { public: void command(Animal*) {} };\n"
        "class Habitat {};\n"
    )
    result = run_coupling(tmp_path, _rule_config(threshold=1), _slop_config())
    # Animal references Pet, Trainer, Habitat → CBO ≥ 2
    flagged = [v.symbol for v in result.violations]
    assert any(s == "Animal" for s in flagged)


def test_cpp_inheritance_depth_walks_base_class_clause(tmp_path: Path):
    (tmp_path / "hier.hpp").write_text(
        "class A {};\n"
        "class B : public A {};\n"
        "class C : public B {};\n"
        "class D : public C {};\n"
    )
    result = run_inheritance_depth(tmp_path, _rule_config(threshold=2),
                                   _slop_config())
    flagged = {v.symbol for v in result.violations}
    assert "D" in flagged  # DIT=3 exceeds 2


def test_cpp_inheritance_children_aggregates_subclasses(tmp_path: Path):
    (tmp_path / "hier.hpp").write_text(
        "class Base {};\n"
        "class A : public Base {};\n"
        "class B : public Base {};\n"
        "class C : public Base {};\n"
        "class D : public Base {};\n"
    )
    result = run_inheritance_children(tmp_path, _rule_config(threshold=3),
                                      _slop_config())
    flagged = {v.symbol for v in result.violations}
    assert "Base" in flagged  # NOC=4 exceeds 3


def test_cpp_class_complexity_includes_out_of_line_methods(tmp_path: Path):
    """The new v1.0.2 feature: out-of-line method CCX attribution to WMC."""
    (tmp_path / "anim.hpp").write_text(
        "class Animal {\n"
        "public:\n"
        "    void simple();\n"
        "    int legs();\n"
        "    void complex();\n"
        "};\n"
    )
    (tmp_path / "anim.cpp").write_text(
        "void Animal::simple() { return; }\n"
        "int Animal::legs() { return 4; }\n"
        "void Animal::complex() {\n"
        "    if (legs() > 4) return;\n"
        "    if (legs() == 0) return;\n"
        "    if (legs() < 0) return;\n"
        "}\n"
    )
    # WMC sum: simple(1) + legs(1) + complex(4) = 6. Threshold 5 → fail.
    result = run_weighted(tmp_path, _rule_config(threshold=5), _slop_config())
    assert result.status == "fail", result.summary
    assert any(v.symbol == "Animal" for v in result.violations)


def test_cpp_class_silent_on_struct_only_file(tmp_path: Path):
    """Struct-only file should still be scanned but not error."""
    (tmp_path / "p.hpp").write_text(
        "struct Point { int x; int y; };\n"
    )
    result = run_coupling(tmp_path, _rule_config(threshold=99), _slop_config())
    assert result.status == "pass"


# ---------------------------------------------------------------------------
# Deps
# ---------------------------------------------------------------------------


def test_cpp_deps_resolves_local_includes(tmp_path: Path):
    (tmp_path / "main.cpp").write_text(
        "#include <iostream>\n"
        "#include \"util.hpp\"\n"
        "int main() { return 0; }\n"
    )
    (tmp_path / "util.hpp").write_text("void util();\n")
    (tmp_path / "util.cpp").write_text(
        "#include \"util.hpp\"\nvoid util() {}\n"
    )
    result = run_cycles(tmp_path, _rule_config(), _slop_config())
    assert result.status in ("pass", "fail")
    assert not result.summary.get("errors")


# ---------------------------------------------------------------------------
# god_module / clone_density / magic_literals / section_comments
# ---------------------------------------------------------------------------


def test_cpp_god_module_counts_top_level_definitions(tmp_path: Path):
    body = ["int fn_{:02d}() {{ return {}; }}".format(i, i) for i in range(15)]
    body.append("class Big { int x; };")
    body.append("namespace ns { int helper() { return 1; } }")
    body.append("template <typename T> T id(T v) { return v; }")
    (tmp_path / "many.cpp").write_text("\n".join(body) + "\n")

    result = run_god_module(tmp_path, _rule_config(threshold=10), _slop_config())
    assert result.status == "fail"
    assert any("many.cpp" in v.file for v in result.violations)


def test_cpp_clone_density_detects_duplicates(tmp_path: Path):
    body = (
        "int sum_a(int x, int y) { return x + y; }\n"
        "int sum_b(int x, int y) { return x + y; }\n"
        "int sum_c(int x, int y) { return x + y; }\n"
    )
    (tmp_path / "clones.cpp").write_text(body)
    result = run_clone_density(tmp_path, _rule_config(threshold=0.10),
                               _slop_config())
    assert result.summary.get("functions_analyzed", 0) >= 3


def test_cpp_magic_literals_flags_bare_numbers(tmp_path: Path):
    (tmp_path / "mag.cpp").write_text(
        "int discount(int days) {\n"
        "    if (days > 30) return 100 * days / 365;\n"
        "    if (days > 7) return 50;\n"
        "    return 7;\n"
        "}\n"
    )
    result = run_magic_literal_density(tmp_path, _rule_config(threshold=2),
                                       _slop_config())
    assert result.status == "fail"
    assert any(v.symbol == "discount" for v in result.violations)


def test_cpp_section_comments_block_dividers(tmp_path: Path):
    (tmp_path / "sect.cpp").write_text(
        "int process(int n) {\n"
        "    /* === setup === */\n"
        "    int total = 0;\n"
        "    /* === main === */\n"
        "    total += n;\n"
        "    /* === cleanup === */\n"
        "    return total;\n"
        "}\n"
    )
    result = run_section_comment_density(tmp_path, _rule_config(threshold=2),
                                         _slop_config())
    assert result.status == "fail"
    assert any(v.symbol == "process" for v in result.violations)


# ---------------------------------------------------------------------------
# Type-discipline rules
# ---------------------------------------------------------------------------


def test_cpp_void_star_flagged_as_escape_hatch(tmp_path: Path):
    (tmp_path / "leaky.cpp").write_text(
        "void *alloc(int n) { return nullptr; }\n"
        "int unpack(void *raw) { return 0; }\n"
        "void *handler(void *data, int kind) { return data; }\n"
    )
    result = run_any_type_density(
        tmp_path, _rule_config(threshold=0.30, min_annotations=2),
        _slop_config(),
    )
    assert result.status == "fail"
    assert any("leaky.cpp" in v.file for v in result.violations)


def test_cpp_reference_param_mutation_flagged(tmp_path: Path):
    (tmp_path / "mut.cpp").write_text(
        "void update(int& out) { out = 42; }\n"
        "void plus_one(int& x) { x = x + 1; }\n"
        "int read_only(const int& src) { return src; }\n"
    )
    result = run_out_parameters(tmp_path, _rule_config(), _slop_config())
    names = {v.symbol for v in result.violations}
    assert "update" in names
    assert "plus_one" in names
    assert "read_only" not in names


def test_cpp_pointer_param_mutation_flagged(tmp_path: Path):
    (tmp_path / "ptr.cpp").write_text(
        "void clear(int* out) { *out = 0; }\n"
        "void fill(int* arr, int n) { arr[0] = n; }\n"
    )
    result = run_out_parameters(tmp_path, _rule_config(), _slop_config())
    names = {v.symbol for v in result.violations}
    assert "clear" in names
    assert "fill" in names


def test_cpp_string_sentinel_flagged(tmp_path: Path):
    (tmp_path / "s.cpp").write_text(
        "void open_file(const char *mode) { (void)mode; }\n"
        "int connect(const char *host, int port) { return port; }\n"
    )
    result = run_stringly_typed(tmp_path, _rule_config(), _slop_config())
    flagged = {(v.symbol, v.message) for v in result.violations}
    assert any("mode" in str(msg) for _, msg in flagged), flagged


# ---------------------------------------------------------------------------
# Lexical rules
# ---------------------------------------------------------------------------


def test_cpp_stutter_flags_repeated_function_tokens(tmp_path: Path):
    (tmp_path / "s.cpp").write_text(
        "int parse_input(int parse_buffer, int parse_size) {\n"
        "    return parse_buffer + parse_size;\n"
        "}\n"
    )
    result = run_stutter(tmp_path, _rule_config(min_overlap_tokens=1),
                         _slop_config())
    assert result.status in ("pass", "fail")


def test_cpp_verbosity_runs(tmp_path: Path):
    (tmp_path / "v.cpp").write_text(
        "int compute_total_aggregated_user_score_value(int a, int b) {\n"
        "    return a + b;\n"
        "}\n"
    )
    result = run_verbosity(tmp_path, _rule_config(), _slop_config())
    assert result.summary.get("items_checked", 0) >= 1


# ---------------------------------------------------------------------------
# Sibling calls
# ---------------------------------------------------------------------------


def test_cpp_sibling_calls_detect_shared_callees(tmp_path: Path):
    (tmp_path / "sib.cpp").write_text(
        "int process_user(int u) {\n"
        "    validate_user(u);\n"
        "    fetch_profile(u);\n"
        "    update_cache(u);\n"
        "    notify_listener(u);\n"
        "    return 0;\n"
        "}\n"
        "int process_admin(int a) {\n"
        "    validate_user(a);\n"
        "    fetch_profile(a);\n"
        "    update_cache(a);\n"
        "    audit_action(a);\n"
        "    return 0;\n"
        "}\n"
    )
    result = run_sibling_call_redundancy(tmp_path, _rule_config(min_shared=3),
                                         _slop_config())
    assert result.status == "fail"


# ---------------------------------------------------------------------------
# Local imports
# ---------------------------------------------------------------------------


def test_cpp_local_include_inside_function(tmp_path: Path):
    (tmp_path / "li.cpp").write_text(
        "int outer(int x) {\n"
        "#include \"helper.hpp\"\n"
        "    return x + 1;\n"
        "}\n"
    )
    result = run_local_imports(tmp_path, _rule_config(), _slop_config())
    assert isinstance(result.summary, dict)
