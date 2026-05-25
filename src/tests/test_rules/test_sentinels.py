"""Tests for ``types.sentinels`` (stringly-typed parameters)."""
from __future__ import annotations

from pathlib import Path

from slop.linter.rule_config import RuleConfig
from slop.config import Config
from slop.structure.metrics.sentinels import run_sentinels
from slop.tree.tree import Tree


def _structure(root: Path):
    t = Tree(root)
    t.scan()
    return t.structure


def _rc(**overrides) -> RuleConfig:
    max_cardinality = overrides.pop("max_cardinality", 8)
    params: dict = {
        "thresholds": {"parameter": max_cardinality},
        "require_str_annotation": True,
    }
    params.update(overrides)
    return RuleConfig(enabled=True, severity="warning", params=params)


def _sc(tmp_path: Path) -> Config:
    return Config(root=str(tmp_path))


_STRINGLY = """\
def set_log_level(level: str) -> None:
    pass
"""

_NON_SENTINEL_STR = """\
def greet(message: str) -> str:
    return f"Hello, {message}"
"""

_INT_SENTINEL = """\
def set_level(level: int) -> None:
    pass
"""

_UNTYPED_SENTINEL = """\
def change_mode(mode) -> None:
    pass
"""

_MULTI_SENTINEL = """\
def configure(mode: str, status: str, level: str) -> None:
    pass
"""

_TRAILING_UNDERSCORE = """\
def select_type(type_: str) -> None:
    pass
"""


# ---------------------------------------------------------------------------
# Structure.sentinel_parameters — view-method unit tests
# ---------------------------------------------------------------------------


def test_view_detects_sentinel_str_param(tmp_path: Path):
    (tmp_path / "a.py").write_text(_STRINGLY)
    entries = _structure(tmp_path).sentinel_parameters()
    entry = next((e for e in entries if e.function_name == "set_log_level"), None)
    assert entry is not None
    assert entry.param_name == "level"
    assert entry.annotated is True


def test_view_ignores_non_sentinel_str(tmp_path: Path):
    (tmp_path / "a.py").write_text(_NON_SENTINEL_STR)
    entries = _structure(tmp_path).sentinel_parameters()
    assert all(e.function_name != "greet" for e in entries)


def test_view_ignores_int_typed_sentinel(tmp_path: Path):
    (tmp_path / "a.py").write_text(_INT_SENTINEL)
    entries = _structure(tmp_path).sentinel_parameters()
    assert all(e.function_name != "set_level" for e in entries)


def test_view_require_annotation_skips_untyped(tmp_path: Path):
    (tmp_path / "a.py").write_text(_UNTYPED_SENTINEL)
    entries = _structure(tmp_path).sentinel_parameters(require_str_annotation=True)
    assert all(e.function_name != "change_mode" for e in entries)


def test_view_no_annotation_required_detects_untyped(tmp_path: Path):
    (tmp_path / "a.py").write_text(_UNTYPED_SENTINEL)
    entries = _structure(tmp_path).sentinel_parameters(require_str_annotation=False)
    entry = next((e for e in entries if e.function_name == "change_mode"), None)
    assert entry is not None
    assert entry.annotated is False


def test_view_multiple_sentinel_params(tmp_path: Path):
    (tmp_path / "a.py").write_text(_MULTI_SENTINEL)
    entries = _structure(tmp_path).sentinel_parameters()
    fn_entries = [e for e in entries if e.function_name == "configure"]
    assert len(fn_entries) == 3


def test_view_trailing_underscore_param(tmp_path: Path):
    (tmp_path / "a.py").write_text(_TRAILING_UNDERSCORE)
    entries = _structure(tmp_path).sentinel_parameters()
    entry = next((e for e in entries if e.function_name == "select_type"), None)
    assert entry is not None


def test_view_collects_call_site_literals(tmp_path: Path):
    (tmp_path / "lib.py").write_text(_STRINGLY)
    (tmp_path / "main.py").write_text(
        'from lib import set_log_level\n'
        'set_log_level("info")\n'
        'set_log_level("debug")\n'
        'set_log_level("error")\n'
    )
    entries = _structure(tmp_path).sentinel_parameters()
    entry = next((e for e in entries if e.function_name == "set_log_level"), None)
    assert entry is not None
    assert entry.call_site_count == 3
    assert set(entry.call_site_literals) == {"info", "debug", "error"}


# ---------------------------------------------------------------------------
# Rule wrapper tests
# ---------------------------------------------------------------------------


def test_rule_fail_sentinel_str(tmp_path: Path):
    (tmp_path / "a.py").write_text(_STRINGLY)
    result = run_sentinels(_structure(tmp_path), _rc(max_cardinality=0), _sc(tmp_path))
    assert result.status == "fail"
    assert len(result.violations) >= 1
    v = result.violations[0]
    assert v.rule == "sentinels"
    assert "level" in v.message


def test_rule_pass_non_sentinel(tmp_path: Path):
    (tmp_path / "a.py").write_text(_NON_SENTINEL_STR)
    result = run_sentinels(_structure(tmp_path), _rc(), _sc(tmp_path))
    assert result.status == "pass"


def test_rule_violation_metadata_keys(tmp_path: Path):
    (tmp_path / "a.py").write_text(_STRINGLY)
    result = run_sentinels(_structure(tmp_path), _rc(max_cardinality=0), _sc(tmp_path))
    if result.violations:
        v = result.violations[0]
        for key in ("param_name", "annotated", "call_site_literals",
                    "call_site_count", "language"):
            assert key in v.metadata, f"missing key: {key}"


def test_rule_summary_keys(tmp_path: Path):
    (tmp_path / "a.py").write_text(_NON_SENTINEL_STR)
    result = run_sentinels(_structure(tmp_path), _rc(), _sc(tmp_path))
    for key in ("candidates_analyzed", "violations", "max_cardinality"):
        assert key in result.summary, f"missing key: {key}"
