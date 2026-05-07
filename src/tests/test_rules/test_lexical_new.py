"""Tests for the six v1.1.0 lexical rules.

- lexical.verbosity
- lexical.cowards
- lexical.hammers
- lexical.tautology
"""
from __future__ import annotations

from pathlib import Path

from slop.models import RuleConfig, SlopConfig


from slop.rules.verbosity import run_verbosity
from slop.rules.cowards import run_cowards
from slop.rules.tautology import run_tautology
from slop.rules.hammers import run_hammers


def _slop() -> SlopConfig:
    return SlopConfig(rules={}, languages=["python"])


def _rc(**params) -> RuleConfig:
    return RuleConfig(enabled=True, severity="warning", params=params)


# ---------------------------------------------------------------------------
# lexical.verbosity
# ---------------------------------------------------------------------------


def test_name_verbosity_flags_long_function_name(tmp_path: Path):
    (tmp_path / "f.py").write_text(
        "def check_required_binaries_for_python_runtime(): pass\n"
        "def short(): pass\n"
    )
    result = run_verbosity(tmp_path, _rc(), _slop())
    assert result.status == "fail"
    flagged = {v.symbol for v in result.violations}
    assert "check_required_binaries_for_python_runtime" in flagged
    assert "short" not in flagged


def test_name_verbosity_threshold(tmp_path: Path):
    (tmp_path / "f.py").write_text("def a_b_c_d(): pass\n")
    # max_tokens=4 => 4 tokens passes
    result = run_verbosity(tmp_path, _rc(max_tokens=4), _slop())
    assert result.status == "pass"
    # max_tokens=3 => 4 tokens fails
    result = run_verbosity(tmp_path, _rc(max_tokens=3), _slop())
    assert result.status == "fail"


def test_name_verbosity_flags_class_name(tmp_path: Path):
    (tmp_path / "f.py").write_text(
        "class AbstractFooBarBazManager:\n    pass\n"
    )
    result = run_verbosity(tmp_path, _rc(), _slop())
    assert any(v.metadata.get("kind") == "class" for v in result.violations)


def test_name_verbosity_check_classes_off(tmp_path: Path):
    (tmp_path / "f.py").write_text(
        "class AbstractFooBarBaz:\n    pass\n"
    )
    result = run_verbosity(tmp_path, _rc(check_classes=False), _slop())
    assert result.status == "pass"


# ---------------------------------------------------------------------------
# lexical.cowards
# ---------------------------------------------------------------------------


def test_numbered_variants_flags_numeric_suffix(tmp_path: Path):
    (tmp_path / "f.py").write_text(
        "def attempt_1(): pass\n"
        "def attempt_2(): pass\n"
        "def normal(): pass\n"
    )
    result = run_cowards(tmp_path, _rc(), _slop())
    flagged = {v.symbol for v in result.violations}
    assert "attempt_1" in flagged
    assert "attempt_2" in flagged
    assert "normal" not in flagged


def test_numbered_variants_flags_alphabetic_suffix(tmp_path: Path):
    (tmp_path / "f.py").write_text(
        "def parse_old(): pass\n"
        "def parse_new(): pass\n"
        "def fetch_local(): pass\n"
    )
    result = run_cowards(tmp_path, _rc(), _slop())
    flagged = {v.symbol for v in result.violations}
    assert "parse_old" in flagged
    assert "parse_new" in flagged
    assert "fetch_local" in flagged


def test_numbered_variants_skips_short_stems(tmp_path: Path):
    """Single-char stems (a1, x2) are loop vars / array indices."""
    (tmp_path / "f.py").write_text("def a1(): pass\n")
    result = run_cowards(tmp_path, _rc(min_stem_tokens=2), _slop())
    flagged = {v.symbol for v in result.violations}
    assert "a1" not in flagged


# ---------------------------------------------------------------------------
# lexical.hammers
# ---------------------------------------------------------------------------


def test_weasel_words_flags_manager_suffix(tmp_path: Path):
    (tmp_path / "f.py").write_text(
        "class UserManager:\n    pass\n"
        "class Order:\n    pass\n"
    )
    result = run_hammers(tmp_path, _rc(), _slop())
    flagged = {v.symbol for v in result.violations}
    assert "UserManager" in flagged
    assert "Order" not in flagged


def test_weasel_words_severity_override(tmp_path: Path):
    (tmp_path / "f.py").write_text("class FooObject:\n    pass\n")
    result = run_hammers(tmp_path, _rc(), _slop())
    obj_hits = [v for v in result.violations if v.symbol == "FooObject"]
    assert obj_hits
    # Object → severity = error in default profile
    assert obj_hits[0].severity == "error"


def test_weasel_words_module_name_match(tmp_path: Path):
    """A file named utils.py should flag on the module-name position."""
    (tmp_path / "utils.py").write_text("def normal(): pass\n")
    result = run_hammers(tmp_path, _rc(), _slop())
    module_hits = [
        v for v in result.violations
        if v.metadata.get("matched_position") == "module_name"
    ]
    assert module_hits


def test_weasel_words_test_module_exempt(tmp_path: Path):
    """`Spec` suffix is exempt under module_is_test."""
    test_dir = tmp_path / "tests"
    test_dir.mkdir()
    (test_dir / "test_foo.py").write_text("class UserSpec:\n    pass\n")
    result = run_hammers(tmp_path, _rc(), _slop())
    flagged = {v.symbol for v in result.violations}
    assert "UserSpec" not in flagged


def test_weasel_words_custom_terms(tmp_path: Path):
    (tmp_path / "f.py").write_text("class FooFrobnicator:\n    pass\n")
    custom = [
        {"word": "Frobnicator", "positions": ["suffix"], "severity": "warning"}
    ]
    result = run_hammers(tmp_path, _rc(terms=custom), _slop())
    flagged = {v.symbol for v in result.violations}
    assert "FooFrobnicator" in flagged


# ---------------------------------------------------------------------------
# lexical.tautology
# ---------------------------------------------------------------------------


def test_type_tag_suffixes_flags_dict(tmp_path: Path):
    (tmp_path / "f.py").write_text(
        "def a(result_dict: dict[str, int]) -> None: ...\n"
    )
    result = run_tautology(tmp_path, _rc(), _slop())
    flagged = {v.symbol for v in result.violations}
    assert "result_dict" in flagged


def test_type_tag_suffixes_flags_path(tmp_path: Path):
    (tmp_path / "f.py").write_text(
        "from pathlib import Path\n"
        "def x(config_path: Path) -> None: ...\n"
    )
    result = run_tautology(tmp_path, _rc(), _slop())
    flagged = {v.symbol for v in result.violations}
    assert "config_path" in flagged


def test_type_tag_suffixes_skips_legitimate_domain_term(tmp_path: Path):
    """`username: str` — `name` isn't a type-tag suffix in our list."""
    (tmp_path / "f.py").write_text(
        "def a(username: str) -> None: ...\n"
    )
    result = run_tautology(tmp_path, _rc(), _slop())
    flagged = {v.symbol for v in result.violations}
    assert "username" not in flagged


def test_type_tag_suffixes_skips_unmatched_annotation(tmp_path: Path):
    """`item_dict: list[Foo]` — suffix doesn't match annotation type."""
    (tmp_path / "f.py").write_text(
        "def a(item_dict: list) -> None: ...\n"
    )
    result = run_tautology(tmp_path, _rc(), _slop())
    flagged = {v.symbol for v in result.violations}
    assert "item_dict" not in flagged


