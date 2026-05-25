"""Tests for ``types.hidden_mutators`` (parameter mutation detection)."""
from __future__ import annotations

from pathlib import Path

from slop.linter.rule_config import RuleConfig
from slop.config import Config
from slop.structure.metrics.hidden_mutators import run_hidden_mutators
from slop.tree.tree import Tree


def _structure(root: Path):
    t = Tree(root)
    t.scan()
    return t.structure


def _rc(**overrides) -> RuleConfig:
    min_mutations = overrides.pop("min_mutations", 1)
    params: dict = {
        "thresholds": {"function": min_mutations},
        "require_type_annotation": True,
    }
    params.update(overrides)
    return RuleConfig(enabled=True, severity="warning", params=params)


def _sc(tmp_path: Path) -> Config:
    return Config(root=str(tmp_path))


_OUT_PARAM_TYPED = """\
from typing import List

def collect_results(results: List[int], value: int) -> None:
    results.append(value)
    results.extend([value + 1, value + 2])
"""

_OUT_PARAM_UNTYPED = """\
def collect_results(results, value):
    results.append(value)
"""

_NO_MUTATION = """\
from typing import List

def process_items(items: List[int]) -> List[int]:
    return [x * 2 for x in items]
"""

_LOCAL_MUTATION = """\
from typing import List

def build_list(count: int) -> List[int]:
    result: List[int] = []
    result.append(count)
    return result
"""

_DICT_OUT_PARAM = """\
from typing import Dict

def enrich_data(record: Dict[str, int], key: str, value: int) -> None:
    record.update({key: value})
"""

_SET_OUT_PARAM = """\
from typing import Set

def register_item(seen: Set[str], item: str) -> None:
    seen.add(item)
"""


# ---------------------------------------------------------------------------
# Structure.hidden_mutators — view-method unit tests
# ---------------------------------------------------------------------------


def test_view_detects_typed_list_mutation(tmp_path: Path):
    (tmp_path / "a.py").write_text(_OUT_PARAM_TYPED)
    entries = _structure(tmp_path).hidden_mutators()
    entry = next((e for e in entries if e.function_name == "collect_results"), None)
    assert entry is not None
    assert entry.mutation_count == 2
    methods = {m.method for m in entry.mutations}
    assert "append" in methods
    assert "extend" in methods


def test_view_require_annotation_skips_untyped(tmp_path: Path):
    (tmp_path / "a.py").write_text(_OUT_PARAM_UNTYPED)
    entries = _structure(tmp_path).hidden_mutators(require_type_annotation=True)
    assert all(e.function_name != "collect_results" for e in entries)


def test_view_no_annotation_required_detects_untyped(tmp_path: Path):
    (tmp_path / "a.py").write_text(_OUT_PARAM_UNTYPED)
    entries = _structure(tmp_path).hidden_mutators(require_type_annotation=False)
    entry = next((e for e in entries if e.function_name == "collect_results"), None)
    assert entry is not None


def test_view_local_variable_not_flagged(tmp_path: Path):
    (tmp_path / "a.py").write_text(_LOCAL_MUTATION)
    entries = _structure(tmp_path).hidden_mutators()
    assert all(e.function_name != "build_list" for e in entries)


def test_view_no_mutation_returns_empty(tmp_path: Path):
    (tmp_path / "a.py").write_text(_NO_MUTATION)
    entries = _structure(tmp_path).hidden_mutators()
    assert entries == []


def test_view_dict_mutation_detected(tmp_path: Path):
    (tmp_path / "a.py").write_text(_DICT_OUT_PARAM)
    entries = _structure(tmp_path).hidden_mutators()
    entry = next((e for e in entries if e.function_name == "enrich_data"), None)
    assert entry is not None
    assert any(m.method == "update" for m in entry.mutations)


def test_view_set_mutation_detected(tmp_path: Path):
    (tmp_path / "a.py").write_text(_SET_OUT_PARAM)
    entries = _structure(tmp_path).hidden_mutators()
    entry = next((e for e in entries if e.function_name == "register_item"), None)
    assert entry is not None
    assert any(m.method == "add" for m in entry.mutations)


# ---------------------------------------------------------------------------
# Rule wrapper tests
# ---------------------------------------------------------------------------


def test_rule_pass_no_mutations(tmp_path: Path):
    (tmp_path / "a.py").write_text(_NO_MUTATION)
    result = run_hidden_mutators(_structure(tmp_path), _rc(), _sc(tmp_path))
    assert result.status == "pass"
    assert result.violations == []


def test_rule_fail_typed_mutation(tmp_path: Path):
    (tmp_path / "a.py").write_text(_OUT_PARAM_TYPED)
    result = run_hidden_mutators(_structure(tmp_path), _rc(), _sc(tmp_path))
    assert result.status == "fail"
    assert len(result.violations) >= 1
    v = result.violations[0]
    assert v.rule == "hidden_mutators"
    assert v.severity == "warning"
    assert "collect_results" in v.message


def test_rule_violation_metadata_keys(tmp_path: Path):
    (tmp_path / "a.py").write_text(_OUT_PARAM_TYPED)
    result = run_hidden_mutators(_structure(tmp_path), _rc(), _sc(tmp_path))
    assert result.violations
    v = result.violations[0]
    for key in ("language", "mutations", "mutated_params"):
        assert key in v.metadata, f"missing key: {key}"


def test_rule_summary_keys(tmp_path: Path):
    (tmp_path / "a.py").write_text(_NO_MUTATION)
    result = run_hidden_mutators(_structure(tmp_path), _rc(), _sc(tmp_path))
    for key in ("callables_analyzed", "violations", "require_type_annotation"):
        assert key in result.summary, f"missing key: {key}"
