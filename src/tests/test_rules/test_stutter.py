"""Tests for the unified ``lexical.stutter`` rule (v1.2.0).

The v1.1.0 split into ``lexical.stutter.{namespaces, callers,
identifiers}`` was unified back into one hierarchy-aware rule with
per-level toggle parameters. The new rule additionally catches
entity-name stutters (e.g., a method name stuttering with its
class name) — a case the split rules missed.
"""

from __future__ import annotations

from pathlib import Path

from slop.models import RuleConfig, SlopConfig
from slop.rules.stutter import run_stutter


def _rc(**params) -> RuleConfig:
    base = {"min_overlap_tokens": 2}
    base.update(params)
    return RuleConfig(enabled=True, severity="warning", params=base)


# ---------------------------------------------------------------------------
# Module-level stutter: identifier inside function body repeats module name
# ---------------------------------------------------------------------------


def test_stutter_module_overlap(tmp_path: Path):
    (tmp_path / "lidar_utils.py").write_text(
        "def load():\n    lidar_utils_config = {}\n    return lidar_utils_config\n"
    )
    result = run_stutter(tmp_path, _rc(), SlopConfig(root=str(tmp_path)))
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
    result = run_stutter(tmp_path, _rc(), SlopConfig(root=str(tmp_path)))
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
    result = run_stutter(tmp_path, _rc(), SlopConfig(root=str(tmp_path)))
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
    result = run_stutter(tmp_path, _rc(), SlopConfig(root=str(tmp_path)))
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
    result = run_stutter(tmp_path, _rc(), SlopConfig(root=str(tmp_path)))
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
    result = run_stutter(
        tmp_path, _rc(check_functions=False),
        SlopConfig(root=str(tmp_path)),
    )
    function_hits = [v for v in result.violations
                     if v.metadata.get("scope_level") == "function"]
    assert not function_hits


def test_stutter_disable_module_level(tmp_path: Path):
    """check_modules=false suppresses module-scope stutters."""
    (tmp_path / "lidar_utils.py").write_text(
        "def load():\n    lidar_utils_config = {}\n    return lidar_utils_config\n"
    )
    result = run_stutter(
        tmp_path, _rc(check_modules=False),
        SlopConfig(root=str(tmp_path)),
    )
    module_hits = [v for v in result.violations
                   if v.metadata.get("scope_level") == "module"]
    assert not module_hits


# ---------------------------------------------------------------------------
# Compat shim: v1.1.0 stutter sub-rules migrate to v1.2.0 unified rule
# ---------------------------------------------------------------------------


def test_legacy_v110_subrule_table_migrates_to_unified():
    from slop._compat import migrate_legacy_rule_tables
    raw = {
        "lexical": {
            "stutter": {
                "namespaces": {
                    "min_overlap_tokens": 3, "severity": "info", "enabled": True,
                },
            }
        }
    }
    canonical = {"lexical.stutter"}
    migrated, deprecations = migrate_legacy_rule_tables(raw, canonical)
    assert "lexical.stutter" in migrated
    assert migrated["lexical.stutter"]["min_overlap_tokens"] == 3
    assert migrated["lexical.stutter"]["check_modules"] is True
    assert any("lexical.stutter.namespaces" in d for d in deprecations)


def test_legacy_stutter_subrule_name_aliases_to_unified():
    from slop._compat import canonical_rule_name
    for legacy in ("lexical.stutter.namespaces",
                   "lexical.stutter.callers",
                   "lexical.stutter.identifiers"):
        canonical, was_legacy = canonical_rule_name(legacy)
        assert canonical == "lexical.stutter"
        assert was_legacy is True
