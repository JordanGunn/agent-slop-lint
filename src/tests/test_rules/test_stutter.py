"""Tests for lexical.stutter rule."""

from __future__ import annotations

from pathlib import Path

from slop.models import RuleConfig, SlopConfig
from slop.rules.stutter import run_stutter

def test_stutter_module_overlap(tmp_path: Path):
    # Module name is 'lidar_utils' (tokens: lidar, utils)
    # Identifier is 'lidar_utils_config' (tokens: lidar, utils, config)
    # Overlap: lidar, utils (2 tokens) -> fail
    pkg = tmp_path / "lidar_utils.py"
    pkg.write_text("def load():\n    lidar_utils_config = {}\n    return lidar_utils_config\n")
    
    rc = RuleConfig(enabled=True, severity="warning", params={"min_overlap_tokens": 2})
    result = run_stutter(tmp_path, rc, SlopConfig(root=str(tmp_path)))
    
    assert result.status == "fail"
    v = result.violations[0]
    assert "lidar_utils_config" in v.symbol
    assert "module" in v.message
    assert "lidar_utils" in v.message

def test_stutter_function_overlap(tmp_path: Path):
    # Function name 'process_pdf_document'
    # Local variable 'pdf_document_bytes'
    # Overlap: pdf, document (2 tokens) -> fail
    (tmp_path / "a.py").write_text(
        "def process_pdf_document(data):\n"
        "    pdf_document_bytes = data.read()\n"
        "    return pdf_document_bytes\n"
    )
    rc = RuleConfig(enabled=True, severity="warning", params={"min_overlap_tokens": 2})
    result = run_stutter(tmp_path, rc, SlopConfig(root=str(tmp_path)))
    
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
    rc = RuleConfig(enabled=True, severity="warning", params={"min_overlap_tokens": 2})
    result = run_stutter(tmp_path, rc, SlopConfig(root=str(tmp_path)))
    assert result.status == "pass"
