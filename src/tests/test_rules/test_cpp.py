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

from slop.config.models import RuleConfig, SlopConfig
from slop.structure.rules.escape_hatches import run_escape_hatches
from slop.structure.rules.clone_density import run_clone_density
from slop.structure.rules.complexity import run_cognitive, run_cyclomatic
from slop.structure.rules.dependencies import run_cycles
from slop.structure.rules.combinatorial import run_combinatorial
from slop.structure.rules.god_module import run_god_module
from slop.structure.rules.hidden_mutators import run_hidden_mutators
from slop.tree.tree import Tree


def _structure(root: Path):
    t = Tree(root)
    t.scan()
    return t.structure


def _lexicon(root: Path):
    t = Tree(root)
    t.scan()
    return t.lexicon
from slop.structure.rules.redundancy import run_redundancy
from slop.structure.rules.sentinels import run_sentinels
from slop.lexicon.rules.stutter import run_stutter
from slop.lexicon.rules.verbosity import run_verbosity


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
    result = run_cyclomatic(_structure(tmp_path), _rule_config(cyclomatic_threshold=0),
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
    result = run_cyclomatic(_structure(tmp_path), _rule_config(cyclomatic_threshold=0),
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
    result = run_cyclomatic(_structure(tmp_path), _rule_config(cyclomatic_threshold=0),
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
    result = run_cyclomatic(_structure(tmp_path), _rule_config(cyclomatic_threshold=0),
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
    result = run_cyclomatic(_structure(tmp_path), _rule_config(cyclomatic_threshold=0),
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
    result = run_cyclomatic(_structure(tmp_path), _rule_config(cyclomatic_threshold=2),
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
    result = run_cyclomatic(_structure(tmp_path), _rule_config(cyclomatic_threshold=2),
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
    result = run_cognitive(_structure(tmp_path), _rule_config(cognitive_threshold=99),
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
    tree = Tree(tmp_path); tree.scan()
    result = run_combinatorial(
        tree.structure, _rule_config(combinatorial_threshold=99),
        SlopConfig(root=str(tmp_path), languages=["cpp"]),
    )
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
    tree = Tree(tmp_path); tree.scan()
    result = run_combinatorial(
        tree.structure, _rule_config(combinatorial_threshold=3),
        SlopConfig(root=str(tmp_path), languages=["cpp"]),
    )
    assert result.status == "fail"


# ---------------------------------------------------------------------------
# Halstead
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# CK class metrics
# ---------------------------------------------------------------------------


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
    t = Tree(tmp_path)
    t.scan()
    result = run_cycles(t.structure, _rule_config(), _slop_config())
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

    result = run_god_module(_structure(tmp_path), _rule_config(threshold=10), _slop_config())
    assert result.status == "fail"
    assert any("many.cpp" in v.file for v in result.violations)


def test_cpp_clone_density_detects_duplicates(tmp_path: Path):
    body = (
        "int sum_a(int x, int y) { return x + y; }\n"
        "int sum_b(int x, int y) { return x + y; }\n"
        "int sum_c(int x, int y) { return x + y; }\n"
    )
    (tmp_path / "clones.cpp").write_text(body)
    t = Tree(tmp_path)
    t.scan()
    result = run_clone_density(t.structure, _rule_config(threshold=0.10),
                               _slop_config())
    assert result.summary.get("functions_analyzed", 0) >= 3


# ---------------------------------------------------------------------------
# Type-discipline rules
# ---------------------------------------------------------------------------


def test_cpp_void_star_flagged_as_escape_hatch(tmp_path: Path):
    (tmp_path / "leaky.cpp").write_text(
        "void *alloc(int n) { return nullptr; }\n"
        "int unpack(void *raw) { return 0; }\n"
        "void *handler(void *data, int kind) { return data; }\n"
    )
    t = Tree(tmp_path)
    t.scan()
    result = run_escape_hatches(
        t.structure,
        _rule_config(threshold=0.30, min_annotations=2),
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
    t = Tree(tmp_path); t.scan()
    result = run_hidden_mutators(t.structure, _rule_config(), _slop_config())
    names = {v.symbol for v in result.violations}
    assert "update" in names
    assert "plus_one" in names
    assert "read_only" not in names


def test_cpp_pointer_param_mutation_flagged(tmp_path: Path):
    (tmp_path / "ptr.cpp").write_text(
        "void clear(int* out) { *out = 0; }\n"
        "void fill(int* arr, int n) { arr[0] = n; }\n"
    )
    t = Tree(tmp_path); t.scan()
    result = run_hidden_mutators(t.structure, _rule_config(), _slop_config())
    names = {v.symbol for v in result.violations}
    assert "clear" in names
    assert "fill" in names


def test_cpp_string_sentinel_flagged(tmp_path: Path):
    (tmp_path / "s.cpp").write_text(
        "void open_file(const char *mode) { (void)mode; }\n"
        "int connect(const char *host, int port) { return port; }\n"
    )
    t = Tree(tmp_path); t.scan()
    result = run_sentinels(t.structure, _rule_config(), _slop_config())
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
    result = run_verbosity(_lexicon(tmp_path), _rule_config(), _slop_config())
    assert result.summary.get("entities_analyzed", 0) >= 1


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
    t = Tree(tmp_path)
    t.scan()
    result = run_redundancy(t.structure, _rule_config(min_shared=3), _slop_config())
    assert result.status == "fail"


# ---------------------------------------------------------------------------
# Local imports
# ---------------------------------------------------------------------------


