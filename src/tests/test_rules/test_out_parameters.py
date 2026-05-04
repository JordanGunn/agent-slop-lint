"""Tests for structural.out_parameters rule."""

from __future__ import annotations

from pathlib import Path

from slop._structural.out_parameters import out_parameters_kernel
from slop.models import RuleConfig, SlopConfig
from slop.rules.out_parameters import run_out_parameters

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _rc(**overrides) -> RuleConfig:
    params = {"require_type_annotation": True, "min_mutations": 1}
    params.update(overrides)
    return RuleConfig(enabled=True, severity="warning", params=params)


def _sc(tmp_path: Path) -> SlopConfig:
    return SlopConfig(root=str(tmp_path))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

# Typed list parameter that is mutated — should be detected
_OUT_PARAM_TYPED = """\
from typing import List

def collect_results(results: List[int], value: int) -> None:
    results.append(value)
    results.extend([value + 1, value + 2])
"""

# Untyped parameter that is mutated — only detected with require_type_annotation=False
_OUT_PARAM_UNTYPED = """\
def collect_results(results, value):
    results.append(value)
"""

# Typed parameter but no mutation — clean function
_NO_MUTATION = """\
from typing import List

def process_items(items: List[int]) -> List[int]:
    return [x * 2 for x in items]
"""

# Local variable mutation — should NOT be flagged (not a parameter)
_LOCAL_MUTATION = """\
from typing import List

def build_list(count: int) -> List[int]:
    result: List[int] = []
    result.append(count)
    return result
"""

# Dict parameter mutation
_DICT_OUT_PARAM = """\
from typing import Dict

def enrich_data(record: Dict[str, int], key: str, value: int) -> None:
    record.update({key: value})
"""

# Set parameter mutation
_SET_OUT_PARAM = """\
from typing import Set

def register_item(seen: Set[str], item: str) -> None:
    seen.add(item)
"""


# ---------------------------------------------------------------------------
# Kernel tests
# ---------------------------------------------------------------------------


def test_kernel_detects_typed_list_mutation(tmp_path: Path):
    (tmp_path / "a.py").write_text(_OUT_PARAM_TYPED)
    result = out_parameters_kernel(tmp_path)
    assert len(result.entries) >= 1
    entry = next(e for e in result.entries if e.name == "collect_results")
    assert entry.mutation_count == 2  # append + extend
    methods = {m.method for m in entry.mutations}
    assert "append" in methods
    assert "extend" in methods


def test_kernel_require_annotation_skips_untyped(tmp_path: Path):
    (tmp_path / "a.py").write_text(_OUT_PARAM_UNTYPED)
    result = out_parameters_kernel(tmp_path, require_type_annotation=True)
    assert all(e.name != "collect_results" for e in result.entries)


def test_kernel_no_annotation_required_detects_untyped(tmp_path: Path):
    (tmp_path / "a.py").write_text(_OUT_PARAM_UNTYPED)
    result = out_parameters_kernel(tmp_path, require_type_annotation=False)
    entry = next((e for e in result.entries if e.name == "collect_results"), None)
    assert entry is not None


def test_kernel_local_variable_not_flagged(tmp_path: Path):
    (tmp_path / "a.py").write_text(_LOCAL_MUTATION)
    result = out_parameters_kernel(tmp_path)
    # `result` is a local variable, not a parameter
    assert all(e.name != "build_list" for e in result.entries)


def test_kernel_no_mutation_returns_empty(tmp_path: Path):
    (tmp_path / "a.py").write_text(_NO_MUTATION)
    result = out_parameters_kernel(tmp_path)
    assert result.entries == []


def test_kernel_dict_mutation_detected(tmp_path: Path):
    (tmp_path / "a.py").write_text(_DICT_OUT_PARAM)
    result = out_parameters_kernel(tmp_path)
    entry = next((e for e in result.entries if e.name == "enrich_data"), None)
    assert entry is not None
    assert any(m.method == "update" for m in entry.mutations)


def test_kernel_set_mutation_detected(tmp_path: Path):
    (tmp_path / "a.py").write_text(_SET_OUT_PARAM)
    result = out_parameters_kernel(tmp_path)
    entry = next((e for e in result.entries if e.name == "register_item"), None)
    assert entry is not None
    assert any(m.method == "add" for m in entry.mutations)


# ---------------------------------------------------------------------------
# Rule wrapper tests
# ---------------------------------------------------------------------------


def test_rule_pass_no_mutations(tmp_path: Path):
    (tmp_path / "a.py").write_text(_NO_MUTATION)
    result = run_out_parameters(tmp_path, _rc(), _sc(tmp_path))
    assert result.status == "pass"
    assert result.violations == []


def test_rule_fail_typed_mutation(tmp_path: Path):
    (tmp_path / "a.py").write_text(_OUT_PARAM_TYPED)
    result = run_out_parameters(tmp_path, _rc(), _sc(tmp_path))
    assert result.status == "fail"
    assert len(result.violations) >= 1
    v = result.violations[0]
    assert v.rule == "structural.types.hidden_mutators"
    assert v.severity == "warning"
    assert "collect_results" in v.message


def test_rule_violation_metadata_keys(tmp_path: Path):
    (tmp_path / "a.py").write_text(_OUT_PARAM_TYPED)
    result = run_out_parameters(tmp_path, _rc(), _sc(tmp_path))
    assert result.violations
    v = result.violations[0]
    for key in ("language", "mutations", "mutated_params"):
        assert key in v.metadata, f"missing key: {key}"


def test_rule_summary_keys(tmp_path: Path):
    (tmp_path / "a.py").write_text(_NO_MUTATION)
    result = run_out_parameters(tmp_path, _rc(), _sc(tmp_path))
    for key in ("functions_analyzed", "files_searched", "violations",
                "require_type_annotation"):
        assert key in result.summary, f"missing key: {key}"
