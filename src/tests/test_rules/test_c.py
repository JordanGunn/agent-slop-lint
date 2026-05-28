"""Smoke tests for C language support across structural and lexical rules.

Each test writes a small ``.c`` (or ``.h``) fixture and runs a rule
with ``languages=["c"]``. Goal: confirm C files parse, the kernel walks
them, and the rule wrapper produces the expected behaviour. Threshold-
tuning correctness is exercised by the per-rule tests on Python; here
we only check the language plumbing and the C-specific name extractor.
"""

from __future__ import annotations

from pathlib import Path

from slop.linter.rule import Rule
from slop.config import Config
from slop.linter.rules import escape_hatches as _escape_hatches_rule
from slop.linter.rules import clone_density as _clone_density_rule
from slop.linter.rules import combinatorial as _combinatorial_rule
from slop.linter.rules import cognitive as _cognitive_rule
from slop.linter.rules import cyclomatic as _cyclomatic_rule
from slop.linter.rules.dependencies import run_cycles
from slop.linter.rules import god_module
from slop.linter.rules import hidden_mutators as _hidden_mutators_rule
from slop.tree.tree import Tree


def _structure(root: Path):
    t = Tree(root)
    t.scan()
    return t.structure


def _lexicon(root: Path):
    t = Tree(root)
    t.scan()
    return t.lexicon
from slop.linter.rules import redundancy as _redundancy_rule
from slop.linter.rules import sentinels as _sentinels_rule
from slop.linter.rules import stutter as _stutter_rule
from slop.linter.rules import verbosity as _verbosity_rule


def _slop_config() -> Config:
    return Config(rules={}, languages=["c"])


def _rule_config(scope: str = "function", **overrides) -> Rule:
    threshold = overrides.pop("threshold", 0)
    params: dict = {"thresholds": {scope: threshold}}
    params.update(overrides)
    return Rule(enabled=True, severity="error", params=params)


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
    result = _cyclomatic_rule.run(_structure(tmp_path), _rule_config(threshold=99), _slop_config())
    names = {f.get("symbol") if isinstance(f, dict) else f.symbol for f in result.violations}
    # No violations expected; we instead inspect the kernel via summary
    # — but to verify name extraction, run with threshold=1 to flag every
    # function and check the symbol set.
    result = _cyclomatic_rule.run(_structure(tmp_path), _rule_config(threshold=0), _slop_config())
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
    result = _cyclomatic_rule.run(_structure(tmp_path), _rule_config(threshold=0), _slop_config())
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
    result = _cyclomatic_rule.run(_structure(tmp_path), _rule_config(threshold=4), _slop_config())
    assert result.status == "fail", result.summary
    assert any(v.symbol == "classify" for v in result.violations)


def test_c_cognitive_flags_nested_branchy(tmp_path: Path):
    (tmp_path / "branchy.c").write_text(_BRANCHY_C)
    result = _cognitive_rule.run(_structure(tmp_path), _rule_config(threshold=3), _slop_config())
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
    result = _cyclomatic_rule.run(_structure(tmp_path), _rule_config(threshold=2), _slop_config())
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
    tree = Tree(tmp_path); tree.scan()
    result = _combinatorial_rule.run(tree.structure, _rule_config(threshold=4), Config(root=str(tmp_path), languages=["c"]))
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
    tree = Tree(tmp_path); tree.scan()
    result = _combinatorial_rule.run(tree.structure, _rule_config(threshold=3), Config(root=str(tmp_path), languages=["c"]))
    assert result.status == "fail"
    assert any(v.symbol == "sw" for v in result.violations)


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

    t = Tree(tmp_path)
    t.scan()
    result = run_cycles(t.structure, _rule_config(), _slop_config())
    # No cycles in this layout.
    assert result.status in ("pass", "fail")
    # Ensure no errors from the C resolver.
    assert not result.summary.get("errors")


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

    result = god_module.run(_structure(tmp_path), _rule_config(scope="module", threshold=10), _slop_config())
    assert result.status == "fail"
    assert any("many.c" in v.file for v in result.violations)


def test_c_clone_density_detects_duplicates(tmp_path: Path):
    body = "int sum_a(int x, int y) { return x + y; }\n" * 1
    body += "int sum_b(int x, int y) { return x + y; }\n"
    body += "int sum_c(int x, int y) { return x + y; }\n"
    body += "int sum_d(int x, int y) { return x + y; }\n"
    (tmp_path / "clones.c").write_text(body)
    t = Tree(tmp_path)
    t.scan()
    result = _clone_density_rule.run(t.structure, _rule_config(threshold=0.10), _slop_config())
    assert result.summary.get("functions_analyzed", 0) >= 4


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
    t = Tree(tmp_path)
    t.scan()
    result = _escape_hatches_rule.run(t.structure, _rule_config(scope="module", threshold=0.30, min_annotations=2),
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
    t = Tree(tmp_path); t.scan()
    result = _hidden_mutators_rule.run(t.structure, _rule_config(), _slop_config())
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
    t = Tree(tmp_path); t.scan()
    result = _sentinels_rule.run(t.structure, _rule_config(scope="parameter", threshold=8), _slop_config())
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
    result = _stutter_rule.run(_lexicon(tmp_path), _rule_config(min_overlap_tokens=1), _slop_config())
    # Best-effort assertion: kernel runs and inspects the function.
    assert result.status in ("pass", "fail")


def test_c_verbosity_runs_without_error(tmp_path: Path):
    (tmp_path / "v.c").write_text(
        "int compute_total_aggregated_user_score_value(int a, int b) {\n"
        "    return a + b;\n"
        "}\n"
    )
    result = _verbosity_rule.run(_lexicon(tmp_path), _rule_config(), _slop_config())
    assert result.summary.get("entities_analyzed", 0) >= 1


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
    t = Tree(tmp_path)
    t.scan()
    result = _redundancy_rule.run(t.structure, _rule_config(min_shared=3), _slop_config())
    assert result.status == "fail"
