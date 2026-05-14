"""Tests for ``structural.redundancy`` (sibling-callee overlap)."""
from __future__ import annotations

from pathlib import Path

from slop.config.models import RuleConfig, SlopConfig
from slop.structure.rules.redundancy import run_redundancy
from slop.tree.tree import Tree


def _structure(root: Path):
    t = Tree(root)
    t.scan()
    return t.structure


def _rc(**overrides) -> RuleConfig:
    params = {"min_shared": 2, "min_score": 0.4}
    params.update(overrides)
    return RuleConfig(enabled=True, severity="warning", params=params)


def _sc(tmp_path: Path) -> SlopConfig:
    return SlopConfig(root=str(tmp_path))


_HIGH_OVERLAP = """\
def validate_user(user):
    check_permissions(user)
    verify_token(user)
    audit_access(user)
    log_event(user)
    return True

def validate_admin(admin):
    check_permissions(admin)
    verify_token(admin)
    audit_access(admin)
    log_event(admin)
    require_mfa(admin)
    return True
"""

_NO_OVERLAP = """\
def fetch_data(url):
    parse_url(url)
    make_request(url)
    return process_response(url)

def persist_record(record):
    validate_schema(record)
    serialize_data(record)
    write_to_db(record)
    return record
"""

_BUILTINS_ONLY = """\
def process_numbers(items):
    return sorted([abs(x) for x in items])

def process_strings(items):
    return sorted([str(x) for x in items])
"""

_THREE_FUNS = """\
def run_step_a(ctx):
    initialize_context(ctx)
    load_config(ctx)
    validate_input(ctx)
    start_timer(ctx)

def run_step_b(ctx):
    initialize_context(ctx)
    load_config(ctx)
    validate_input(ctx)
    apply_transform(ctx)

def run_step_c(ctx):
    finalize_output(ctx)
    cleanup_temp_files(ctx)
"""


# ---------------------------------------------------------------------------
# Structure.redundant_siblings — view-method unit tests
# ---------------------------------------------------------------------------


def test_view_detects_high_overlap_pair(tmp_path: Path):
    (tmp_path / "a.py").write_text(_HIGH_OVERLAP)
    pairs = _structure(tmp_path).redundant_siblings(min_shared=3, min_score=0.4)
    assert len(pairs) >= 1
    pair = pairs[0]
    assert {"validate_user", "validate_admin"} == {pair.fn_a, pair.fn_b}
    assert len(pair.shared_callees) >= 4
    assert pair.score > 0.4


def test_view_no_pairs_for_non_overlapping_functions(tmp_path: Path):
    (tmp_path / "a.py").write_text(_NO_OVERLAP)
    pairs = _structure(tmp_path).redundant_siblings(min_shared=2, min_score=0.4)
    assert pairs == []


def test_view_builtin_calls_excluded(tmp_path: Path):
    (tmp_path / "a.py").write_text(_BUILTINS_ONLY)
    pairs = _structure(tmp_path).redundant_siblings(min_shared=1, min_score=0.1)
    assert pairs == []


def test_view_three_functions_correct_pairs(tmp_path: Path):
    (tmp_path / "a.py").write_text(_THREE_FUNS)
    pairs = _structure(tmp_path).redundant_siblings(min_shared=2, min_score=0.3)
    pair_names = {(p.fn_a, p.fn_b) for p in pairs}
    assert ("run_step_a", "run_step_b") in pair_names or \
           ("run_step_b", "run_step_a") in pair_names


def test_view_pairs_sorted_by_score_desc(tmp_path: Path):
    (tmp_path / "a.py").write_text(_HIGH_OVERLAP)
    pairs = _structure(tmp_path).redundant_siblings(min_shared=1, min_score=0.0)
    scores = [p.score for p in pairs]
    assert scores == sorted(scores, reverse=True)


def test_view_thin_wrappers_not_flagged(tmp_path: Path):
    """Four thin wrappers each calling only _wrap must not be flagged.

    They share one callee (score=100%) but ``|shared| = 1 < min_shared = 3``.
    """
    (tmp_path / "color.py").write_text("""\
def red(s):
    return _wrap(s, "31")

def green(s):
    return _wrap(s, "32")

def yellow(s):
    return _wrap(s, "33")

def bold(s):
    return _wrap(s, "1")
""")
    pairs = _structure(tmp_path).redundant_siblings(min_shared=3, min_score=0.5)
    assert pairs == []


# ---------------------------------------------------------------------------
# Rule wrapper tests
# ---------------------------------------------------------------------------


def test_rule_fail_high_overlap(tmp_path: Path):
    (tmp_path / "a.py").write_text(_HIGH_OVERLAP)
    result = run_redundancy(
        _structure(tmp_path), _rc(min_shared=3, min_score=0.4), _sc(tmp_path),
    )
    assert result.status == "fail"
    assert len(result.violations) >= 1
    v = result.violations[0]
    assert v.rule == "structural.redundancy"
    assert v.severity == "warning"


def test_rule_pass_no_overlap(tmp_path: Path):
    (tmp_path / "a.py").write_text(_NO_OVERLAP)
    result = run_redundancy(_structure(tmp_path), _rc(), _sc(tmp_path))
    assert result.status == "pass"
    assert result.violations == []


def test_rule_violation_metadata_keys(tmp_path: Path):
    (tmp_path / "a.py").write_text(_HIGH_OVERLAP)
    result = run_redundancy(
        _structure(tmp_path), _rc(min_shared=2, min_score=0.2), _sc(tmp_path),
    )
    if result.violations:
        v = result.violations[0]
        for key in ("fn_a", "fn_b", "shared_callees", "score"):
            assert key in v.metadata, f"missing key: {key}"


def test_rule_summary_keys(tmp_path: Path):
    (tmp_path / "a.py").write_text(_NO_OVERLAP)
    result = run_redundancy(_structure(tmp_path), _rc(), _sc(tmp_path))
    for key in ("pair_violations", "min_shared", "min_score"):
        assert key in result.summary, f"missing key: {key}"
