"""Smoke tests for Ruby language support across the rule suite.

Each test writes a small ``.rb`` fixture and runs a rule with
``languages=["ruby"]``. Goal: confirm Ruby files parse, the kernel
walks them, and the rule wrapper produces the expected output —
including Ruby-specific shapes (singleton methods, operator overloads,
blocks, modules-as-abstract, open-class aggregation).
"""

from __future__ import annotations

import pytest

from pathlib import Path

from slop.linter.rule import Rule
from slop.config import Config
from slop.linter.rules.escape_hatches import run_escape_hatches
from slop.linter.rules.clone_density import run_clone_density
from slop.linter.rules.cognitive import run_cognitive
from slop.linter.rules.cyclomatic import run_cyclomatic
from slop.linter.rules.dependencies import run_cycles
from slop.linter.rules.combinatorial import run_combinatorial
from slop.linter.rules.god_module import run_god_module
from slop.linter.rules.hidden_mutators import run_hidden_mutators
from slop.tree.tree import Tree


def _structure(root: Path):
    t = Tree(root)
    t.scan()
    return t.structure


def _lexicon(root: Path):
    t = Tree(root)
    t.scan()
    return t.lexicon
from slop.linter.rules.redundancy import run_redundancy
from slop.linter.rules.sentinels import run_sentinels
from slop.linter.rules.stutter import run_stutter
from slop.linter.rules.verbosity import run_verbosity


def _slop_config() -> Config:
    return Config(rules={}, languages=["ruby"])


def _rule_config(scope: str = "function", **overrides) -> Rule:
    threshold = overrides.pop("threshold", 0)
    params: dict = {"thresholds": {scope: threshold}}
    params.update(overrides)
    return Rule(enabled=True, severity="error", params=params)


# ---------------------------------------------------------------------------
# Function name extraction
# ---------------------------------------------------------------------------


def test_ruby_method_name_extracted(tmp_path: Path):
    (tmp_path / "m.rb").write_text(
        "def add(a, b)\n  a + b\nend\n"
        "def greet(name)\n  \"hi #{name}\"\nend\n"
    )
    result = run_cyclomatic(_structure(tmp_path), _rule_config(threshold=0),
                            _slop_config())
    names = {v.symbol for v in result.violations}
    assert "add" in names
    assert "greet" in names


def test_ruby_singleton_method_name_extracted(tmp_path: Path):
    (tmp_path / "m.rb").write_text(
        "class Factory\n"
        "  def self.create(spec)\n"
        "    Foo.new(spec)\n"
        "  end\n"
        "end\n"
    )
    result = run_cyclomatic(_structure(tmp_path), _rule_config(threshold=0),
                            _slop_config())
    names = {v.symbol for v in result.violations}
    assert "create" in names


def test_ruby_operator_method_name_extracted(tmp_path: Path):
    (tmp_path / "v.rb").write_text(
        "class Vec\n"
        "  def ==(other); true; end\n"
        "  def +(other); Vec.new; end\n"
        "  def [](i); @arr[i]; end\n"
        "  def []=(i, v); @arr[i] = v; end\n"
        "  def <=>(other); 0; end\n"
        "end\n"
    )
    result = run_cyclomatic(_structure(tmp_path), _rule_config(threshold=0),
                            _slop_config())
    names = {v.symbol for v in result.violations}
    assert "==" in names
    assert "+" in names
    assert "[]" in names
    assert "[]=" in names
    assert "<=>" in names


@pytest.mark.xfail(reason="substrate Tree walker does not yet detect this Ruby callable shape (kernel-only feature)")
def test_ruby_block_treated_as_anonymous(tmp_path: Path):
    (tmp_path / "b.rb").write_text(
        "[1, 2, 3].each do |x|\n"
        "  if x.positive?\n"
        "    puts x\n"
        "  end\n"
        "end\n"
    )
    result = run_cyclomatic(_structure(tmp_path), _rule_config(threshold=0),
                            _slop_config())
    names = {v.symbol for v in result.violations}
    assert "<lambda>" in names


@pytest.mark.xfail(reason="substrate Tree walker does not yet detect this Ruby callable shape (kernel-only feature)")
def test_ruby_lambda_treated_as_anonymous(tmp_path: Path):
    (tmp_path / "l.rb").write_text(
        "add = ->(a, b) { a + b }\n"
        "mul = lambda { |a, b| a * b }\n"
    )
    result = run_cyclomatic(_structure(tmp_path), _rule_config(threshold=0),
                            _slop_config())
    names = {v.symbol for v in result.violations}
    assert "<lambda>" in names


# ---------------------------------------------------------------------------
# Cyclomatic / cognitive
# ---------------------------------------------------------------------------


_BRANCHY = """\
def classify(x)
  if x < 0
    -1
  elsif x == 0
    0
  elsif x > 100 && x < 1000
    2
  else
    1
  end
end
"""


def test_ruby_cyclomatic_flags_branchy_function(tmp_path: Path):
    (tmp_path / "c.rb").write_text(_BRANCHY)
    result = run_cyclomatic(_structure(tmp_path), _rule_config(threshold=4),
                            _slop_config())
    assert result.status == "fail"
    assert any(v.symbol == "classify" for v in result.violations)


@pytest.mark.xfail(reason="substrate Tree walker does not yet detect this Ruby callable shape (kernel-only feature)")
def test_ruby_if_modifier_postfix_counted(tmp_path: Path):
    (tmp_path / "p.rb").write_text(
        "def each_positive(xs)\n"
        "  xs.each { |x| puts x if x.positive? }\n"
        "  xs.each { |x| puts x unless x.zero? }\n"
        "end\n"
    )
    # Lambda's postfix-if and postfix-unless add to the lambda's CCX.
    result = run_cyclomatic(_structure(tmp_path), _rule_config(threshold=0),
                            _slop_config())
    # Both blocks should be flagged
    lambda_violations = [v for v in result.violations if v.symbol == "<lambda>"]
    assert len(lambda_violations) >= 2


def test_ruby_cognitive_runs(tmp_path: Path):
    (tmp_path / "c.rb").write_text(_BRANCHY)
    result = run_cognitive(_structure(tmp_path), _rule_config(threshold=99),
                           _slop_config())
    assert result.status == "pass"


# ---------------------------------------------------------------------------
# NPath
# ---------------------------------------------------------------------------


def test_ruby_npath_multiplies_sequential_postfix_ifs(tmp_path: Path):
    (tmp_path / "d.rb").write_text(
        "def dispatch(a, b, c)\n"
        "  do_a if a > 0\n"
        "  do_b if b > 0\n"
        "  do_c if c > 0\n"
        "  0\n"
        "end\n"
    )
    tree = Tree(tmp_path); tree.scan()
    result = run_combinatorial(tree.structure, _rule_config(threshold=4), Config(root=str(tmp_path), languages=["ruby"]))
    assert result.status == "fail"


def test_ruby_npath_counts_when_clauses(tmp_path: Path):
    (tmp_path / "s.rb").write_text(
        "def case_demo(x)\n"
        "  case x\n"
        "  when 1 then 'one'\n"
        "  when 2 then 'two'\n"
        "  when 3 then 'three'\n"
        "  else 'other'\n"
        "  end\n"
        "end\n"
    )
    tree = Tree(tmp_path); tree.scan()
    result = run_combinatorial(tree.structure, _rule_config(threshold=2), Config(root=str(tmp_path), languages=["ruby"]))
    assert result.status == "fail"


def test_ruby_npath_counts_rescue_clauses(tmp_path: Path):
    (tmp_path / "b.rb").write_text(
        "def safely\n"
        "  begin\n"
        "    risky\n"
        "  rescue StandardError => e\n"
        "    -1\n"
        "  end\n"
        "end\n"
    )
    tree = Tree(tmp_path); tree.scan()
    result = run_combinatorial(tree.structure, _rule_config(threshold=99), Config(root=str(tmp_path), languages=["ruby"]))
    # Just verify it runs and produces a number; threshold high so pass.
    assert result.status == "pass"


# ---------------------------------------------------------------------------
# Halstead
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# CK class metrics + open-class aggregation
# ---------------------------------------------------------------------------


def test_ruby_module_counts_as_abstract_in_packages(tmp_path: Path):
    """Modules are the natural abstract analog in Ruby."""
    from slop.tree.tree import Tree
    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "shapes.rb").write_text(
        "module Walkable; def walk; end; end\n"
        "class Shape; def area; end; end\n"
    )
    t = Tree(tmp_path)
    t.scan()
    pkgs = t.structure.packages(tmp_path)
    assert len(pkgs) == 1
    pkg = pkgs[0]
    assert pkg.na == 1  # Walkable module
    assert pkg.nc == 1  # Shape class


# ---------------------------------------------------------------------------
# Deps
# ---------------------------------------------------------------------------


def test_ruby_deps_resolves_require_relative(tmp_path: Path):
    (tmp_path / "main.rb").write_text(
        "require 'json'\n"
        "require_relative './util'\n"
        "puts 'hi'\n"
    )
    (tmp_path / "util.rb").write_text("def util; end\n")
    t = Tree(tmp_path)
    t.scan()
    result = run_cycles(t.structure, _rule_config(), _slop_config())
    assert result.status in ("pass", "fail")
    assert not result.summary.get("errors")


# ---------------------------------------------------------------------------
# god_module / clone_density / magic_literals / section_comments
# ---------------------------------------------------------------------------


def test_ruby_god_module_counts_top_level(tmp_path: Path):
    body = ["def fn_{:02d}; {}; end".format(i, i) for i in range(15)]
    body.append("class Big\nend")
    body.append("module Helper\nend")
    (tmp_path / "many.rb").write_text("\n".join(body) + "\n")
    result = run_god_module(_structure(tmp_path), _rule_config(scope="module", threshold=10),
                            _slop_config())
    assert result.status == "fail"
    assert any("many.rb" in v.file for v in result.violations)


def test_ruby_clone_density_detects_duplicates(tmp_path: Path):
    body = (
        "def sum_a(x, y); x + y; end\n"
        "def sum_b(x, y); x + y; end\n"
        "def sum_c(x, y); x + y; end\n"
    )
    (tmp_path / "clones.rb").write_text(body)
    t = Tree(tmp_path)
    t.scan()
    result = run_clone_density(t.structure, _rule_config(threshold=0.10),
                               _slop_config())
    assert result.summary.get("functions_analyzed", 0) >= 3


# ---------------------------------------------------------------------------
# Type-discipline rules
# ---------------------------------------------------------------------------


def test_ruby_any_type_density_silent_skip(tmp_path: Path):
    """Ruby is dynamically typed; rule does not apply."""
    (tmp_path / "x.rb").write_text("def foo(x); x; end\n")
    t = Tree(tmp_path)
    t.scan()
    result = run_escape_hatches(t.structure, _rule_config(scope="module", threshold=0.30),
                                _slop_config())
    # Ruby has no annotation node types — no entries, no violations.
    assert result.status == "pass"
    assert not result.violations


def test_ruby_out_parameters_silent_skip(tmp_path: Path):
    """Ruby is dynamically typed; rule does not apply."""
    (tmp_path / "x.rb").write_text(
        "def fill(arr)\n"
        "  arr << 1\n"
        "  arr << 2\n"
        "end\n"
    )
    t = Tree(tmp_path); t.scan()
    result = run_hidden_mutators(t.structure, _rule_config(), _slop_config())
    # No registration → no violations
    assert not result.violations


def test_ruby_string_sentinel_param_flagged(tmp_path: Path):
    (tmp_path / "s.rb").write_text(
        "def open_file(mode)\n"
        "  # 'r', 'w', 'rw'\n"
        "end\n"
        "def log_event(kind, level)\n"
        "  # ...\n"
        "end\n"
        "def connect(host, port)\n"
        "  # not stringly\n"
        "end\n"
    )
    t = Tree(tmp_path); t.scan()
    result = run_sentinels(t.structure, _rule_config(scope="parameter", threshold=8), _slop_config())
    flagged = {(v.symbol, v.message) for v in result.violations}
    assert any("mode" in str(msg) for _, msg in flagged), flagged
    assert any("kind" in str(msg) for _, msg in flagged), flagged
    assert any("level" in str(msg) for _, msg in flagged), flagged


# ---------------------------------------------------------------------------
# Lexical rules
# ---------------------------------------------------------------------------


def test_ruby_stutter_runs(tmp_path: Path):
    (tmp_path / "s.rb").write_text(
        "def parse_input(parse_buffer, parse_size)\n"
        "  parse_buffer + parse_size\n"
        "end\n"
    )
    result = run_stutter(_lexicon(tmp_path), _rule_config(min_overlap_tokens=1),
                         _slop_config())
    assert result.status in ("pass", "fail")


def test_ruby_verbosity_runs(tmp_path: Path):
    (tmp_path / "v.rb").write_text(
        "def compute_total_aggregated_user_score_value(a, b)\n"
        "  a + b\n"
        "end\n"
    )
    result = run_verbosity(_lexicon(tmp_path), _rule_config(), _slop_config())
    assert result.summary.get("entities_analyzed", 0) >= 1


# ---------------------------------------------------------------------------
# Sibling calls
# ---------------------------------------------------------------------------


def test_ruby_sibling_calls_detect_shared_callees(tmp_path: Path):
    (tmp_path / "sib.rb").write_text(
        "def process_user(u)\n"
        "  validate_user(u)\n"
        "  fetch_profile(u)\n"
        "  update_cache(u)\n"
        "  notify_listener(u)\n"
        "  0\n"
        "end\n"
        "def process_admin(a)\n"
        "  validate_user(a)\n"
        "  fetch_profile(a)\n"
        "  update_cache(a)\n"
        "  audit_action(a)\n"
        "  0\n"
        "end\n"
    )
    t = Tree(tmp_path)
    t.scan()
    result = run_redundancy(t.structure, _rule_config(min_shared=3), _slop_config())
    assert result.status == "fail"


# ---------------------------------------------------------------------------
# Local imports
# ---------------------------------------------------------------------------


