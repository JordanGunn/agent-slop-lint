"""Tests for the unified ``lexical.stutter`` rule (v1.2.0).

The v1.1.0 split into ``lexical.stutter.{namespaces, callers,
identifiers}`` was unified back into one hierarchy-aware rule with
per-level toggle parameters. The new rule additionally catches
entity-name stutters (e.g., a method name stuttering with its
class name) — a case the split rules missed.
"""

from __future__ import annotations

from pathlib import Path

from slop.linter.rule import Rule
from slop.config import Config
from slop.linter.rules import stutter as _stutter_rule
from slop.tree.tree import Tree


def _lexicon(root):
    t = Tree(root)
    t.scan()
    return t.lexicon



def _rc(**params) -> Rule:
    base = {"min_overlap_tokens": 2}
    base.update(params)
    return Rule(enabled=True, severity="warning", params=base)


# ---------------------------------------------------------------------------
# Module-level stutter: identifier inside function body repeats module name
# ---------------------------------------------------------------------------


def test_stutter_module_overlap(tmp_path: Path):
    (tmp_path / "lidar_utils.py").write_text(
        "def load():\n    lidar_utils_config = {}\n    return lidar_utils_config\n"
    )
    result = _stutter_rule.run(_lexicon(tmp_path), _rc(), Config(root=str(tmp_path)))
    assert result.status == "fail"
    module_hits = [v for v in result.violations
                   if v.metadata.get("scope_level") == "module"]
    assert module_hits, "expected at least one module-level stutter"


# ---------------------------------------------------------------------------
# Function-level stutter: identifier inside body repeats function name
# ---------------------------------------------------------------------------


def test_stutter_function_overlap(tmp_path: Path):
    (tmp_path / "a.py").write_text(
        "def process_pdf_document(data):\n"
        "    pdf_document_bytes = data.read()\n"
        "    return pdf_document_bytes\n"
    )
    result = _stutter_rule.run(_lexicon(tmp_path), _rc(), Config(root=str(tmp_path)))
    assert result.status == "fail"
    function_hits = [v for v in result.violations
                     if v.metadata.get("scope_level") == "function"]
    assert function_hits


# ---------------------------------------------------------------------------
# Class-level stutter: identifier inside method body repeats class name
# ---------------------------------------------------------------------------


def test_stutter_class_overlap(tmp_path: Path):
    (tmp_path / "a.py").write_text(
        "class UserService:\n"
        "    def get(self):\n"
        "        user_service_helper = self.helper\n"
        "        return user_service_helper\n"
    )
    result = _stutter_rule.run(_lexicon(tmp_path), _rc(), Config(root=str(tmp_path)))
    assert result.status == "fail"
    class_hits = [v for v in result.violations
                  if v.metadata.get("scope_level") == "class"]
    assert class_hits


# ---------------------------------------------------------------------------
# Entity-name stutter (NEW in v1.2.0): the entity's own name stutters
# with its enclosing scope.
# ---------------------------------------------------------------------------


def test_stutter_method_name_stutters_with_class(tmp_path: Path):
    """Method NAME (not body identifiers) stuttering with class name —
    the case the v1.1.0 split rules missed."""
    (tmp_path / "a.py").write_text(
        "class UserService:\n"
        "    def get_user_service_id(self):\n"
        "        return 1\n"
    )
    result = _stutter_rule.run(_lexicon(tmp_path), _rc(), Config(root=str(tmp_path)))
    assert result.status == "fail"
    name_hits = [v for v in result.violations
                 if v.metadata.get("is_entity_name") is True]
    assert name_hits, "expected method-name stutter against class"
    assert name_hits[0].symbol == "get_user_service_id"
    assert name_hits[0].metadata.get("scope_level") == "class"


# ---------------------------------------------------------------------------
# Negative case: no stutter
# ---------------------------------------------------------------------------


def test_stutter_no_overlap_pass(tmp_path: Path):
    (tmp_path / "a.py").write_text(
        "def process(data):\n"
        "    content = data.read()\n"
        "    return content\n"
    )
    result = _stutter_rule.run(_lexicon(tmp_path), _rc(), Config(root=str(tmp_path)))
    assert result.status == "pass"


# ---------------------------------------------------------------------------
# Per-level toggle parameters
# ---------------------------------------------------------------------------


def test_stutter_disable_function_level(tmp_path: Path):
    """check_functions=false suppresses function-scope stutters."""
    (tmp_path / "a.py").write_text(
        "def process_pdf_document(data):\n"
        "    pdf_document_bytes = data.read()\n"
        "    return pdf_document_bytes\n"
    )
    result = _stutter_rule.run(
        _lexicon(tmp_path), _rc(check_functions=False),
        Config(root=str(tmp_path)),
    )
    function_hits = [v for v in result.violations
                     if v.metadata.get("scope_level") == "function"]
    assert not function_hits


def test_stutter_disable_module_level(tmp_path: Path):
    """check_modules=false suppresses module-scope stutters."""
    (tmp_path / "lidar_utils.py").write_text(
        "def load():\n    lidar_utils_config = {}\n    return lidar_utils_config\n"
    )
    result = _stutter_rule.run(
        _lexicon(tmp_path), _rc(check_modules=False),
        Config(root=str(tmp_path)),
    )
    module_hits = [v for v in result.violations
                   if v.metadata.get("scope_level") == "module"]
    assert not module_hits


