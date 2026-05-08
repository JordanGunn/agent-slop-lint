"""Tests for lexical.confusion (v1.2.0).

File-level Extract Class detection per Lanza & Marinescu (2006).
"""
from __future__ import annotations

from pathlib import Path

from slop.models import RuleConfig, SlopConfig
from slop.rules.confusion import run_confusion


def _slop() -> SlopConfig:
    return SlopConfig(rules={}, languages=["python"])


def _rc(**params) -> RuleConfig:
    return RuleConfig(enabled=True, severity="warning", params=params)


def test_confusion_flags_multi_receiver_file(tmp_path: Path):
    """File with two distinct strong-receiver clusters fires."""
    (tmp_path / "output.py").write_text(
        # 5 functions clustering on `result` with receiver-call use
        "def format_human(result):\n"
        "    return result.summary\n"
        "def format_quiet(result):\n"
        "    return result.summary\n"
        "def format_json(result):\n"
        "    return result.violations\n"
        "def render_footer(result):\n"
        "    return result.errors\n"
        "def aggregate_metrics(result):\n"
        "    return result.metrics\n"
        # 3 functions clustering on `category` with receiver-call use
        "def render_category(category):\n"
        "    return category.name\n"
        "def aggregate_category(category):\n"
        "    return category.violations\n"
        "def header_extras(category):\n"
        "    return category.window\n"
    )
    result = run_confusion(tmp_path, _rc(), _slop())
    assert result.status == "fail"
    flagged = {v.symbol for v in result.violations}
    assert any("output.py" in f for f in flagged)


def test_confusion_passes_for_single_cluster_file(tmp_path: Path):
    """File with one cluster (regardless of size) doesn't fire."""
    (tmp_path / "renderer.py").write_text(
        "def format_human(result):\n"
        "    return result.summary\n"
        "def format_quiet(result):\n"
        "    return result.summary\n"
        "def format_json(result):\n"
        "    return result.violations\n"
        "def render_footer(result):\n"
        "    return result.errors\n"
    )
    result = run_confusion(tmp_path, _rc(), _slop())
    assert result.status == "pass"


def test_confusion_skips_small_file(tmp_path: Path):
    """File below min_functions threshold doesn't fire even with multiple clusters."""
    (tmp_path / "tiny.py").write_text(
        "def fa(result): return result.x\n"
        "def fb(result): return result.y\n"
        "def fc(result): return result.z\n"
        "def ga(other): return other.a\n"
    )
    result = run_confusion(tmp_path, _rc(min_functions=10), _slop())
    assert result.status == "pass"
