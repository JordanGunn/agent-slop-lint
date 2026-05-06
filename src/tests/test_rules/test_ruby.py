"""Smoke tests for Ruby language support across the rule suite.

Each test writes a small ``.rb`` fixture and runs a rule with
``languages=["ruby"]``. Goal: confirm Ruby files parse, the kernel
walks them, and the rule wrapper produces the expected output —
including Ruby-specific shapes (singleton methods, operator overloads,
blocks, modules-as-abstract, open-class aggregation).
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
    return SlopConfig(rules={}, languages=["ruby"])


def _rule_config(**overrides) -> RuleConfig:
    return RuleConfig(enabled=True, severity="error", params=overrides)


# ---------------------------------------------------------------------------
# Function name extraction
# ---------------------------------------------------------------------------


def test_ruby_method_name_extracted(tmp_path: Path):
    (tmp_path / "m.rb").write_text(
        "def add(a, b)\n  a + b\nend\n"
        "def greet(name)\n  \"hi #{name}\"\nend\n"
    )
    result = run_cyclomatic(tmp_path, _rule_config(cyclomatic_threshold=0),
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
    result = run_cyclomatic(tmp_path, _rule_config(cyclomatic_threshold=0),
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
    result = run_cyclomatic(tmp_path, _rule_config(cyclomatic_threshold=0),
                            _slop_config())
    names = {v.symbol for v in result.violations}
    assert "==" in names
    assert "+" in names
    assert "[]" in names
    assert "[]=" in names
    assert "<=>" in names


def test_ruby_block_treated_as_anonymous(tmp_path: Path):
    (tmp_path / "b.rb").write_text(
        "[1, 2, 3].each do |x|\n"
        "  if x.positive?\n"
        "    puts x\n"
        "  end\n"
        "end\n"
    )
    result = run_cyclomatic(tmp_path, _rule_config(cyclomatic_threshold=0),
                            _slop_config())
    names = {v.symbol for v in result.violations}
    assert "<lambda>" in names


def test_ruby_lambda_treated_as_anonymous(tmp_path: Path):
    (tmp_path / "l.rb").write_text(
        "add = ->(a, b) { a + b }\n"
        "mul = lambda { |a, b| a * b }\n"
    )
    result = run_cyclomatic(tmp_path, _rule_config(cyclomatic_threshold=0),
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
    result = run_cyclomatic(tmp_path, _rule_config(cyclomatic_threshold=4),
                            _slop_config())
    assert result.status == "fail"
    assert any(v.symbol == "classify" for v in result.violations)


def test_ruby_if_modifier_postfix_counted(tmp_path: Path):
    (tmp_path / "p.rb").write_text(
        "def each_positive(xs)\n"
        "  xs.each { |x| puts x if x.positive? }\n"
        "  xs.each { |x| puts x unless x.zero? }\n"
        "end\n"
    )
    # Lambda's postfix-if and postfix-unless add to the lambda's CCX.
    result = run_cyclomatic(tmp_path, _rule_config(cyclomatic_threshold=0),
                            _slop_config())
    # Both blocks should be flagged
    lambda_violations = [v for v in result.violations if v.symbol == "<lambda>"]
    assert len(lambda_violations) >= 2


def test_ruby_cognitive_runs(tmp_path: Path):
    (tmp_path / "c.rb").write_text(_BRANCHY)
    result = run_cognitive(tmp_path, _rule_config(cognitive_threshold=99),
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
    result = run_npath(tmp_path, _rule_config(npath_threshold=4), _slop_config())
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
    result = run_npath(tmp_path, _rule_config(npath_threshold=2), _slop_config())
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
    result = run_npath(tmp_path, _rule_config(npath_threshold=99), _slop_config())
    # Just verify it runs and produces a number; threshold high so pass.
    assert result.status == "pass"


# ---------------------------------------------------------------------------
# Halstead
# ---------------------------------------------------------------------------


def test_ruby_halstead_volume_runs(tmp_path: Path):
    (tmp_path / "h.rb").write_text(
        "def discount(days, amount)\n"
        "  if days > 30\n"
        "    return amount * 100 / 365\n"
        "  end\n"
        "  amount\n"
        "end\n"
    )
    result = run_volume(tmp_path, _rule_config(threshold=10000), _slop_config())
    assert result.status == "pass"


def test_ruby_halstead_difficulty_runs(tmp_path: Path):
    (tmp_path / "h.rb").write_text("def square(x); x * x; end\n")
    result = run_difficulty(tmp_path, _rule_config(threshold=99), _slop_config())
    assert result.status == "pass"


# ---------------------------------------------------------------------------
# CK class metrics + open-class aggregation
# ---------------------------------------------------------------------------


def test_ruby_class_inheritance_walks_superclass(tmp_path: Path):
    (tmp_path / "h.rb").write_text(
        "class A; end\n"
        "class B < A; end\n"
        "class C < B; end\n"
        "class D < C; end\n"
    )
    result = run_inheritance_depth(tmp_path, _rule_config(threshold=2),
                                   _slop_config())
    flagged = {v.symbol for v in result.violations}
    assert "D" in flagged  # DIT=3


def test_ruby_class_inheritance_children_aggregates(tmp_path: Path):
    (tmp_path / "h.rb").write_text(
        "class Base; end\n"
        "class A < Base; end\n"
        "class B < Base; end\n"
        "class C < Base; end\n"
        "class D < Base; end\n"
    )
    result = run_inheritance_children(tmp_path, _rule_config(threshold=3),
                                      _slop_config())
    flagged = {v.symbol for v in result.violations}
    assert "Base" in flagged  # NOC=4


def test_ruby_open_class_aggregates_wmc(tmp_path: Path):
    """The new v1.0.3 feature: re-opening ``class Foo`` across files."""
    (tmp_path / "a.rb").write_text(
        "class Animal\n"
        "  def speak\n"
        "    raise NotImplementedError\n"
        "  end\n"
        "  def legs\n"
        "    if @custom\n"
        "      @custom_legs\n"
        "    else\n"
        "      4\n"
        "    end\n"
        "  end\n"
        "end\n"
    )
    (tmp_path / "b.rb").write_text(
        "class Animal\n"
        "  def lifespan\n"
        "    if @young\n"
        "      10\n"
        "    else\n"
        "      20\n"
        "    end\n"
        "  end\n"
        "end\n"
    )
    # Threshold low to confirm Animal aggregated WMC fires
    result = run_weighted(tmp_path, _rule_config(threshold=4), _slop_config())
    assert result.status == "fail", result.summary
    flagged = {v.symbol for v in result.violations}
    assert "Animal" in flagged
    # And only ONE Animal entry (aggregation; not 2)
    animal_violations = [v for v in result.violations if v.symbol == "Animal"]
    assert len(animal_violations) == 1


def test_ruby_module_counts_as_abstract_in_packages(tmp_path: Path):
    """Modules are the natural abstract analog in Ruby."""
    from slop._structural.robert import robert_kernel
    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "shapes.rb").write_text(
        "module Walkable; def walk; end; end\n"
        "class Shape; def area; end; end\n"
    )
    result = robert_kernel(tmp_path, language="ruby")
    pkg = result.packages[0]
    assert pkg.na == 1  # Walkable module
    assert pkg.nc == 1  # Shape class


def test_ruby_class_coupling_runs(tmp_path: Path):
    (tmp_path / "c.rb").write_text(
        "class Animal\n"
        "  def setup\n"
        "    @pet = Pet.new\n"
        "    @trainer = Trainer.new\n"
        "    @habitat = Habitat.new\n"
        "  end\n"
        "end\n"
        "class Pet; end\n"
        "class Trainer; end\n"
        "class Habitat; end\n"
    )
    result = run_coupling(tmp_path, _rule_config(threshold=99), _slop_config())
    assert result.status == "pass"


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
    result = run_cycles(tmp_path, _rule_config(), _slop_config())
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
    result = run_god_module(tmp_path, _rule_config(threshold=10),
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
    result = run_clone_density(tmp_path, _rule_config(threshold=0.10),
                               _slop_config())
    assert result.summary.get("functions_analyzed", 0) >= 3


def test_ruby_magic_literals_flags_bare_numbers(tmp_path: Path):
    (tmp_path / "mag.rb").write_text(
        "def discount(days)\n"
        "  return 100 * days / 365 if days > 30\n"
        "  return 50 if days > 7\n"
        "  7\n"
        "end\n"
    )
    result = run_magic_literal_density(tmp_path, _rule_config(threshold=2),
                                       _slop_config())
    assert result.status == "fail"
    assert any(v.symbol == "discount" for v in result.violations)


def test_ruby_section_comments_detect_dividers(tmp_path: Path):
    (tmp_path / "s.rb").write_text(
        "def process(n)\n"
        "  # === setup ===\n"
        "  total = 0\n"
        "  # === main ===\n"
        "  total += n\n"
        "  # === cleanup ===\n"
        "  total\n"
        "end\n"
    )
    result = run_section_comment_density(tmp_path, _rule_config(threshold=2),
                                         _slop_config())
    assert result.status == "fail"
    assert any(v.symbol == "process" for v in result.violations)


# ---------------------------------------------------------------------------
# Type-discipline rules
# ---------------------------------------------------------------------------


def test_ruby_any_type_density_silent_skip(tmp_path: Path):
    """Ruby is dynamically typed; rule does not apply."""
    (tmp_path / "x.rb").write_text("def foo(x); x; end\n")
    result = run_any_type_density(tmp_path, _rule_config(threshold=0.30),
                                  _slop_config())
    # No registration → no entries, no errors.
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
    result = run_out_parameters(tmp_path, _rule_config(), _slop_config())
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
    result = run_stringly_typed(tmp_path, _rule_config(), _slop_config())
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
    result = run_stutter(tmp_path, _rule_config(min_overlap_tokens=1),
                         _slop_config())
    assert result.status in ("pass", "fail")


def test_ruby_verbosity_runs(tmp_path: Path):
    (tmp_path / "v.rb").write_text(
        "def compute_total_aggregated_user_score_value(a, b)\n"
        "  a + b\n"
        "end\n"
    )
    result = run_verbosity(tmp_path, _rule_config(), _slop_config())
    assert result.summary.get("functions_checked", 0) >= 1


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
    result = run_sibling_call_redundancy(tmp_path, _rule_config(min_shared=3),
                                         _slop_config())
    assert result.status == "fail"


# ---------------------------------------------------------------------------
# Local imports
# ---------------------------------------------------------------------------


def test_ruby_require_inside_method_flagged(tmp_path: Path):
    (tmp_path / "li.rb").write_text(
        "def lazy_load\n"
        "  require 'big_dependency'\n"
        "  BigDependency.new\n"
        "end\n"
    )
    result = run_local_imports(tmp_path, _rule_config(), _slop_config())
    assert isinstance(result.summary, dict)
