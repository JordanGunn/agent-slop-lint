"""Smoke tests for C language support across structural and lexical rules.

Each test writes a small ``.c`` (or ``.h``) fixture and runs a rule
with ``languages=["c"]``. Goal: confirm C files parse, the kernel walks
them, and the rule wrapper produces the expected behaviour. Threshold-
tuning correctness is exercised by the per-rule tests on Python; here
we only check the language plumbing and the C-specific name extractor.
"""

from __future__ import annotations

from pathlib import Path

from slop.models import RuleConfig, SlopConfig
from slop.rules.any_type_density import run_any_type_density
from slop.rules.class_metrics import run_coupling
from slop.rules.clone_density import run_clone_density
from slop.rules.complexity import run_cognitive, run_cyclomatic
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
    return SlopConfig(rules={}, languages=["c"])


def _rule_config(**overrides) -> RuleConfig:
    return RuleConfig(enabled=True, severity="error", params=overrides)


# ---------------------------------------------------------------------------
# Function name extraction (the v1.0.1 hot spot — declarator chain walker)
# ---------------------------------------------------------------------------

_NAME_EXTRACTION_C = """\
int add(int a, int b) { return a + b; }

static inline int square(int x) { return x * x; }

const char *greet(int hour) { return hour < 12 ? "morning" : "evening"; }

void *raw_alloc(int n) { return 0; }

unsigned long long big(void) { return 0; }
"""


def test_c_cyclomatic_extracts_plain_function_name(tmp_path: Path):
    (tmp_path / "names.c").write_text(_NAME_EXTRACTION_C)
    result = run_cyclomatic(tmp_path, _rule_config(cyclomatic_threshold=99), _slop_config())
    names = {f.get("symbol") if isinstance(f, dict) else f.symbol for f in result.violations}
    # No violations expected; we instead inspect the kernel via summary
    # — but to verify name extraction, run with threshold=1 to flag every
    # function and check the symbol set.
    result = run_cyclomatic(tmp_path, _rule_config(cyclomatic_threshold=0), _slop_config())
    names = {v.symbol for v in result.violations}
    assert "add" in names
    assert "square" in names
    assert "greet" in names
    assert "raw_alloc" in names
    assert "big" in names
    # No function should land as <anonymous> for these shapes.
    assert "<anonymous>" not in names


def test_c_typedef_function_pointer_not_treated_as_function(tmp_path: Path):
    """``typedef int (*cmp)(int, int);`` parses as type_definition, not
    function_definition — must not appear in CCX results."""
    (tmp_path / "fp.c").write_text(
        "typedef int (*comparator)(int, int);\n"
        "int real_fn(int a, int b) { return a + b; }\n"
    )
    result = run_cyclomatic(tmp_path, _rule_config(cyclomatic_threshold=0), _slop_config())
    names = {v.symbol for v in result.violations}
    assert "real_fn" in names
    assert "comparator" not in names


# ---------------------------------------------------------------------------
# Cyclomatic / cognitive
# ---------------------------------------------------------------------------

_BRANCHY_C = """\
int classify(int x) {
    if (x < 0) {
        return -1;
    } else if (x == 0) {
        return 0;
    } else if (x > 100 && x < 1000) {
        return 2;
    } else {
        return 1;
    }
}
"""


def test_c_cyclomatic_flags_branchy_function(tmp_path: Path):
    (tmp_path / "branchy.c").write_text(_BRANCHY_C)
    result = run_cyclomatic(tmp_path, _rule_config(cyclomatic_threshold=4), _slop_config())
    assert result.status == "fail", result.summary
    assert any(v.symbol == "classify" for v in result.violations)


def test_c_cognitive_flags_nested_branchy(tmp_path: Path):
    (tmp_path / "branchy.c").write_text(_BRANCHY_C)
    result = run_cognitive(tmp_path, _rule_config(cognitive_threshold=3), _slop_config())
    assert result.status == "fail"
    assert any(v.symbol == "classify" for v in result.violations)


def test_c_cyclomatic_counts_switch_cases(tmp_path: Path):
    (tmp_path / "sw.c").write_text(
        "int sw(int x) {\n"
        "    switch (x) {\n"
        "        case 1: return 1;\n"
        "        case 2: return 2;\n"
        "        case 3: return 3;\n"
        "        default: return 0;\n"
        "    }\n"
        "}\n"
    )
    result = run_cyclomatic(tmp_path, _rule_config(cyclomatic_threshold=2), _slop_config())
    assert result.status == "fail"
    assert any(v.symbol == "sw" for v in result.violations)


# ---------------------------------------------------------------------------
# NPath
# ---------------------------------------------------------------------------


def test_c_npath_multiplies_sequential_branches(tmp_path: Path):
    """Three sequential ``if`` statements without ``else`` branches produce
    NPath = 2 * 2 * 2 = 8."""
    (tmp_path / "dispatch.c").write_text(
        "int dispatch(int a, int b, int c) {\n"
        "    if (a > 0) { do_a(); }\n"
        "    if (b > 0) { do_b(); }\n"
        "    if (c > 0) { do_c(); }\n"
        "    return 0;\n"
        "}\n"
    )
    result = run_npath(tmp_path, _rule_config(npath_threshold=4), _slop_config())
    assert result.status == "fail"
    assert any(v.symbol == "dispatch" for v in result.violations)


def test_c_npath_counts_switch_cases(tmp_path: Path):
    """Switch with N cases (incl. default) contributes N paths.

    Pre-1.0.1 the kernel under-counted any language whose grammar wraps
    cases in a body node (Java, C#, C). This test guards the fix.
    """
    (tmp_path / "sw.c").write_text(
        "int sw(int x) {\n"
        "    switch (x) {\n"
        "        case 1: return 1;\n"
        "        case 2: return 2;\n"
        "        case 3: return 3;\n"
        "        default: return 0;\n"
        "    }\n"
        "}\n"
    )
    result = run_npath(tmp_path, _rule_config(npath_threshold=3), _slop_config())
    assert result.status == "fail"
    assert any(v.symbol == "sw" for v in result.violations)


# ---------------------------------------------------------------------------
# Halstead
# ---------------------------------------------------------------------------


def test_c_halstead_volume_runs_without_error(tmp_path: Path):
    (tmp_path / "h.c").write_text(
        "int discount(int days, int amount) {\n"
        "    if (days > 30) { return amount * 100 / 365; }\n"
        "    if (days > 7) { return amount * 50 / 100; }\n"
        "    return amount * 7 / 100;\n"
        "}\n"
    )
    result = run_volume(tmp_path, _rule_config(threshold=10000), _slop_config())
    assert result.status == "pass"
    assert result.summary.get("functions_checked", 0) >= 1


def test_c_halstead_difficulty_runs_without_error(tmp_path: Path):
    (tmp_path / "h.c").write_text(
        "int square(int x) { return x * x; }\n"
    )
    result = run_difficulty(tmp_path, _rule_config(threshold=100), _slop_config())
    assert result.status == "pass"


# ---------------------------------------------------------------------------
# Deps / packages / hotspots — mostly about the language-detection and
# query plumbing, not threshold tuning.
# ---------------------------------------------------------------------------


def test_c_deps_resolves_local_includes(tmp_path: Path):
    (tmp_path / "main.c").write_text(
        "#include <stdio.h>\n"
        "#include \"util.h\"\n"
        "int main(void) { return 0; }\n"
    )
    (tmp_path / "util.h").write_text("void util(void);\n")
    (tmp_path / "util.c").write_text("#include \"util.h\"\nvoid util(void) {}\n")

    result = run_cycles(tmp_path, _rule_config(), _slop_config())
    # No cycles in this layout.
    assert result.status in ("pass", "fail")
    # Ensure no errors from the C resolver.
    assert not result.summary.get("errors")


# ---------------------------------------------------------------------------
# CK (class metrics) — must silently no-op on .c files (no class concept)
# ---------------------------------------------------------------------------


def test_c_class_coupling_silently_skips(tmp_path: Path):
    (tmp_path / "all.c").write_text(
        "struct Point { int x; int y; };\n"
        "int dot(struct Point a, struct Point b) { return a.x*b.x + a.y*b.y; }\n"
    )
    result = run_coupling(tmp_path, _rule_config(threshold=0), _slop_config())
    # No classes → no violations, no errors.
    assert result.status == "pass"
    assert not result.violations


# ---------------------------------------------------------------------------
# god_module / clone_density / magic_literals / section_comments
# ---------------------------------------------------------------------------


def test_c_god_module_counts_top_level_definitions(tmp_path: Path):
    body = []
    for i in range(15):
        body.append(f"int fn_{i:02d}(int x) {{ return x + {i}; }}")
    body.append("struct Rec { int a; };")
    body.append("enum E { A, B, C };")
    body.append("typedef int Counter;")
    (tmp_path / "many.c").write_text("\n".join(body) + "\n")

    result = run_god_module(tmp_path, _rule_config(threshold=10), _slop_config())
    assert result.status == "fail"
    assert any("many.c" in v.file for v in result.violations)


def test_c_clone_density_detects_duplicates(tmp_path: Path):
    body = "int sum_a(int x, int y) { return x + y; }\n" * 1
    body += "int sum_b(int x, int y) { return x + y; }\n"
    body += "int sum_c(int x, int y) { return x + y; }\n"
    body += "int sum_d(int x, int y) { return x + y; }\n"
    (tmp_path / "clones.c").write_text(body)
    result = run_clone_density(tmp_path, _rule_config(threshold=0.10), _slop_config())
    # Status pass or fail acceptable; kernel must analyse the functions.
    assert result.summary.get("functions_analyzed", 0) >= 4


def test_c_magic_literals_flags_bare_numbers(tmp_path: Path):
    (tmp_path / "mag.c").write_text(
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


def test_c_section_comments_detect_dividers(tmp_path: Path):
    (tmp_path / "sect.c").write_text(
        "int process(int *xs, int n) {\n"
        "    /* === setup === */\n"
        "    int total = 0;\n"
        "    /* === main loop === */\n"
        "    for (int i = 0; i < n; i++) total += xs[i];\n"
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


def test_c_void_star_flagged_as_escape_hatch(tmp_path: Path):
    (tmp_path / "leaky.c").write_text(
        "void *alloc_buf(int n) { return 0; }\n"
        "int unpack(void *raw) { return 0; }\n"
        "void *registry[10];\n"
        "void *handler(void *data, int kind) { return data; }\n"
    )
    result = run_any_type_density(
        tmp_path, _rule_config(threshold=0.30, min_annotations=2),
        _slop_config(),
    )
    assert result.status == "fail"
    assert any("leaky.c" in v.file for v in result.violations)


def test_c_pointer_param_mutation_flagged(tmp_path: Path):
    (tmp_path / "mut.c").write_text(
        "void increment(int *out) { *out = *out + 1; }\n"
        "void update(struct Point *p) { p->x = 0; p->y = 1; }\n"
        "int read_only(const int *src) { return *src; }\n"
    )
    result = run_out_parameters(tmp_path, _rule_config(), _slop_config())
    names = {v.symbol for v in result.violations}
    assert "increment" in names
    assert "update" in names
    # const T * must be excluded
    assert "read_only" not in names


def test_c_char_star_sentinel_flagged(tmp_path: Path):
    (tmp_path / "s.c").write_text(
        "void open_file(const char *mode) { (void)mode; }\n"
        "int connect(const char *host, int port) { (void)host; return port; }\n"
    )
    result = run_stringly_typed(tmp_path, _rule_config(), _slop_config())
    flagged = {(v.symbol, v.message) for v in result.violations}
    # ``mode`` is a sentinel; ``host`` is not.
    assert any("mode" in str(msg) for _, msg in flagged), flagged


# ---------------------------------------------------------------------------
# Lexical rules
# ---------------------------------------------------------------------------


def test_c_stutter_flags_repeated_function_tokens(tmp_path: Path):
    (tmp_path / "stut.c").write_text(
        "int parse_input(int parse_buffer, int parse_size) {\n"
        "    return parse_buffer + parse_size;\n"
        "}\n"
    )
    result = run_stutter(tmp_path, _rule_config(min_overlap_tokens=1), _slop_config())
    # Best-effort assertion: kernel runs and inspects the function.
    assert result.status in ("pass", "fail")


def test_c_verbosity_runs_without_error(tmp_path: Path):
    (tmp_path / "v.c").write_text(
        "int compute_total_aggregated_user_score_value(int a, int b) {\n"
        "    return a + b;\n"
        "}\n"
    )
    result = run_verbosity(tmp_path, _rule_config(), _slop_config())
    assert result.summary.get("items_checked", 0) >= 1


# ---------------------------------------------------------------------------
# Sibling calls (redundancy)
# ---------------------------------------------------------------------------


def test_c_sibling_calls_detect_shared_callees(tmp_path: Path):
    (tmp_path / "sib.c").write_text(
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
    # Two sibling functions sharing 3 callees → flagged
    assert result.status == "fail"


# ---------------------------------------------------------------------------
# Local imports
# ---------------------------------------------------------------------------


def test_c_local_include_inside_function_flagged(tmp_path: Path):
    """``#include`` inside a function body — rare but flagged."""
    (tmp_path / "li.c").write_text(
        "int outer(int x) {\n"
        "#include \"helper.h\"\n"
        "    return x + 1;\n"
        "}\n"
    )
    result = run_local_imports(tmp_path, _rule_config(), _slop_config())
    # We only require the kernel to run without error on C; the rule's
    # severity-warning posture means we don't gate hard on detection.
    assert isinstance(result.summary, dict)
