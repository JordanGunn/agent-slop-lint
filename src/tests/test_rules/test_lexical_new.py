"""Tests for the v1.1.0 lexical rules.

- lexical.verbosity
- lexical.hammers
"""
from __future__ import annotations

from pathlib import Path

from slop.linter.rule import Rule
from slop.config import Config
from slop.tree.tree import Tree


def _structure(root: Path):
    t = Tree(root)
    t.scan()
    return t.structure


def _lexicon(root: Path):
    t = Tree(root)
    t.scan()
    return t.lexicon


from slop.linter.rules import verbosity as _verbosity_rule
from slop.linter.rules import hammers as _hammers_rule


def _slop() -> Config:
    return Config(rules={}, languages=["python"])


def _rc(**params) -> Rule:
    return Rule(enabled=True, severity="warning", params=params)


# ---------------------------------------------------------------------------
# lexical.verbosity
# ---------------------------------------------------------------------------


def test_name_verbosity_flags_long_function_name(tmp_path: Path):
    (tmp_path / "f.py").write_text(
        "def check_required_binaries_for_python_runtime(): pass\n"
        "def short(): pass\n"
    )
    result = _verbosity_rule.run(_lexicon(tmp_path), _rc(), _slop())
    assert result.status == "fail"
    flagged = {v.symbol for v in result.violations}
    assert "check_required_binaries_for_python_runtime" in flagged
    assert "short" not in flagged


def test_name_verbosity_threshold(tmp_path: Path):
    (tmp_path / "f.py").write_text("def a_b_c_d(): pass\n")
    # max_tokens=4 => 4 tokens passes
    result = _verbosity_rule.run(_lexicon(tmp_path), _rc(max_tokens=4), _slop())
    assert result.status == "pass"
    # max_tokens=3 => 4 tokens fails
    result = _verbosity_rule.run(_lexicon(tmp_path), _rc(max_tokens=3), _slop())
    assert result.status == "fail"


def test_name_verbosity_flags_class_name(tmp_path: Path):
    (tmp_path / "f.py").write_text(
        "class AbstractFooBarBazManager:\n    pass\n"
    )
    result = _verbosity_rule.run(_lexicon(tmp_path), _rc(), _slop())
    assert any(v.metadata.get("kind") == "class" for v in result.violations)


def test_name_verbosity_check_classes_off(tmp_path: Path):
    (tmp_path / "f.py").write_text(
        "class AbstractFooBarBaz:\n    pass\n"
    )
    result = _verbosity_rule.run(_lexicon(tmp_path), _rc(check_classes=False), _slop())
    assert result.status == "pass"


# ---------------------------------------------------------------------------
# lexical.hammers
# ---------------------------------------------------------------------------


def test_weasel_words_flags_manager_suffix(tmp_path: Path):
    (tmp_path / "f.py").write_text(
        "class UserManager:\n    pass\n"
        "class Order:\n    pass\n"
    )
    result = _hammers_rule.run(_lexicon(tmp_path), _rc(), _slop())
    flagged = {v.symbol for v in result.violations}
    assert "UserManager" in flagged
    assert "Order" not in flagged


def test_weasel_words_severity_override(tmp_path: Path):
    (tmp_path / "f.py").write_text("class FooObject:\n    pass\n")
    result = _hammers_rule.run(_lexicon(tmp_path), _rc(), _slop())
    obj_hits = [v for v in result.violations if v.symbol == "FooObject"]
    assert obj_hits
    # Object → severity = error in default profile
    assert obj_hits[0].severity == "error"


def test_weasel_words_module_name_match(tmp_path: Path):
    """A file named utils.py should flag on the module-name position."""
    (tmp_path / "utils.py").write_text("def normal(): pass\n")
    result = _hammers_rule.run(_lexicon(tmp_path), _rc(), _slop())
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
    result = _hammers_rule.run(_lexicon(tmp_path), _rc(), _slop())
    flagged = {v.symbol for v in result.violations}
    assert "UserSpec" not in flagged


def test_weasel_words_custom_terms(tmp_path: Path):
    (tmp_path / "f.py").write_text("class FooFrobnicator:\n    pass\n")
    custom = [
        {"word": "Frobnicator", "positions": ["suffix"], "severity": "warning"}
    ]
    result = _hammers_rule.run(_lexicon(tmp_path), _rc(terms=custom), _slop())
    flagged = {v.symbol for v in result.violations}
    assert "FooFrobnicator" in flagged



