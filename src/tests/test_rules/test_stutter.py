"""Tests for lexical.stutter.* rules.

The 1.1.0 split replaced the unified ``lexical.stutter`` rule with
three scope-targeted rules. The legacy ``run_stutter`` still works
(it runs all three modes at once) and is exercised here for backward
compatibility.
"""

from __future__ import annotations

from pathlib import Path

from slop.models import RuleConfig, SlopConfig
from slop.rules.stutter import (
    run_stutter,
    run_stutter_callers,
    run_stutter_identifiers,
    run_stutter_namespaces,
)


def _rc(**params) -> RuleConfig:
    base = {"min_overlap_tokens": 2}
    base.update(params)
    return RuleConfig(enabled=True, severity="warning", params=base)


# ---------------------------------------------------------------------------
# Legacy unified rule — kept working for back-compat
# ---------------------------------------------------------------------------


def test_stutter_module_overlap(tmp_path: Path):
    pkg = tmp_path / "lidar_utils.py"
    pkg.write_text(
        "def load():\n    lidar_utils_config = {}\n    return lidar_utils_config\n"
    )
    result = run_stutter(tmp_path, _rc(), SlopConfig(root=str(tmp_path)))
    assert result.status == "fail"
    v = result.violations[0]
    assert "lidar_utils_config" in v.symbol
    assert "module" in v.message


def test_stutter_function_overlap(tmp_path: Path):
    (tmp_path / "a.py").write_text(
        "def process_pdf_document(data):\n"
        "    pdf_document_bytes = data.read()\n"
        "    return pdf_document_bytes\n"
    )
    result = run_stutter(tmp_path, _rc(), SlopConfig(root=str(tmp_path)))
    assert result.status == "fail"
    v = result.violations[0]
    assert "pdf_document_bytes" in v.symbol
    assert "function" in v.message


def test_stutter_no_overlap_pass(tmp_path: Path):
    (tmp_path / "a.py").write_text(
        "def process(data):\n"
        "    content = data.read()\n"
        "    return content\n"
    )
    result = run_stutter(tmp_path, _rc(), SlopConfig(root=str(tmp_path)))
    assert result.status == "pass"


# ---------------------------------------------------------------------------
# lexical.stutter.namespaces — module-scope only
# ---------------------------------------------------------------------------


def test_stutter_namespaces_flags_module_overlap(tmp_path: Path):
    pkg = tmp_path / "lidar_utils.py"
    pkg.write_text(
        "def load():\n    lidar_utils_config = {}\n    return lidar_utils_config\n"
    )
    result = run_stutter_namespaces(tmp_path, _rc(), SlopConfig(root=str(tmp_path)))
    assert result.status == "fail"
    assert any(v.metadata.get("scope_type") == "module" for v in result.violations)


def test_stutter_namespaces_ignores_function_overlap(tmp_path: Path):
    """Function-scope stutter is *not* a namespace stutter."""
    (tmp_path / "a.py").write_text(
        "def process_pdf_document(data):\n"
        "    pdf_document_bytes = data.read()\n"
        "    return pdf_document_bytes\n"
    )
    result = run_stutter_namespaces(tmp_path, _rc(), SlopConfig(root=str(tmp_path)))
    assert result.status == "pass"


# ---------------------------------------------------------------------------
# lexical.stutter.callers — class-scope only
# ---------------------------------------------------------------------------


def test_stutter_callers_flags_class_overlap(tmp_path: Path):
    (tmp_path / "a.py").write_text(
        "class UserService:\n"
        "    def get_user_service_id(self):\n"
        "        return 1\n"
    )
    result = run_stutter_callers(tmp_path, _rc(), SlopConfig(root=str(tmp_path)))
    # Class-scope stutter only fires on identifiers *within* a method
    # body, not the method name itself. Add a body that stutters with
    # the class name:
    (tmp_path / "a.py").write_text(
        "class UserService:\n"
        "    def get(self):\n"
        "        user_service_helper = self.helper\n"
        "        return user_service_helper\n"
    )
    result = run_stutter_callers(tmp_path, _rc(), SlopConfig(root=str(tmp_path)))
    assert result.status == "fail"
    assert any(v.metadata.get("scope_type") == "class" for v in result.violations)


def test_stutter_callers_ignores_module_overlap(tmp_path: Path):
    pkg = tmp_path / "lidar_utils.py"
    pkg.write_text(
        "def load():\n    lidar_utils_config = {}\n    return lidar_utils_config\n"
    )
    result = run_stutter_callers(tmp_path, _rc(), SlopConfig(root=str(tmp_path)))
    assert result.status == "pass"


# ---------------------------------------------------------------------------
# lexical.stutter.identifiers — function-scope only
# ---------------------------------------------------------------------------


def test_stutter_identifiers_flags_function_overlap(tmp_path: Path):
    (tmp_path / "a.py").write_text(
        "def process_pdf_document(data):\n"
        "    pdf_document_bytes = data.read()\n"
        "    return pdf_document_bytes\n"
    )
    result = run_stutter_identifiers(tmp_path, _rc(), SlopConfig(root=str(tmp_path)))
    assert result.status == "fail"
    assert any(v.metadata.get("scope_type") == "function" for v in result.violations)


def test_stutter_identifiers_ignores_module_overlap(tmp_path: Path):
    """Module-scope stutter is *not* an identifier stutter."""
    pkg = tmp_path / "lidar_utils.py"
    pkg.write_text(
        "def load():\n    lidar_utils_config = {}\n    return lidar_utils_config\n"
    )
    result = run_stutter_identifiers(tmp_path, _rc(), SlopConfig(root=str(tmp_path)))
    assert result.status == "pass"


# ---------------------------------------------------------------------------
# Compat shim: legacy [rules.lexical.stutter] table → identifiers
# ---------------------------------------------------------------------------


def test_legacy_stutter_table_migrates_to_identifiers():
    from slop._compat import migrate_legacy_rule_tables
    raw = {"lexical": {"stutter": {"min_overlap_tokens": 3, "severity": "info"}}}
    canonical = {
        "lexical.stutter.namespaces", "lexical.stutter.callers",
        "lexical.stutter.identifiers",
    }
    migrated, deprecations = migrate_legacy_rule_tables(raw, canonical)
    assert "lexical.stutter.identifiers" in migrated
    assert migrated["lexical.stutter.identifiers"]["min_overlap_tokens"] == 3
    assert migrated["lexical.stutter.identifiers"]["severity"] == "info"
    assert any("lexical.stutter" in d for d in deprecations)


def test_legacy_stutter_rule_name_aliases_to_identifiers():
    from slop._compat import canonical_rule_name
    canonical, was_legacy = canonical_rule_name("lexical.stutter")
    assert canonical == "lexical.stutter.identifiers"
    assert was_legacy is True
