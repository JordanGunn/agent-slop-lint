"""Tests for lexical.slackers (v1.2.0).

Slackers fires on real clusters (per the imposters kernel) whose
member names refuse to follow a common naming template.
"""
from __future__ import annotations

from pathlib import Path

from slop.models import RuleConfig, SlopConfig
from slop.rules.slackers import run_slackers


def _slop() -> SlopConfig:
    return SlopConfig(rules={}, languages=["python"])


def _rc(**params) -> RuleConfig:
    return RuleConfig(enabled=True, severity="warning", params=params)


def test_slackers_flags_unaligned_real_cluster(tmp_path: Path):
    """Five functions sharing `customer` with receiver-call use, but no
    common naming template — fires."""
    (tmp_path / "billing.py").write_text(
        "def calculate_invoice_total(customer):\n"
        "    return customer.lines\n"
        "def determine_eligibility(customer):\n"
        "    return customer.tier\n"
        "def serialize_for_audit(customer):\n"
        "    return customer.id\n"
        "def fetch_account_history(customer):\n"
        "    return customer.id\n"
        "def emit_metrics(customer):\n"
        "    return customer.metrics\n"
    )
    result = run_slackers(tmp_path, _rc(), _slop())
    assert result.status == "fail"
    flagged = {v.symbol for v in result.violations}
    assert "customer" in flagged


def test_slackers_passes_when_names_align(tmp_path: Path):
    """Cluster with a clean naming template (`format_*`) doesn't fire."""
    (tmp_path / "renderer.py").write_text(
        "def format_human(result):\n"
        "    return result.summary\n"
        "def format_quiet(result):\n"
        "    return result.summary\n"
        "def format_json(result):\n"
        "    return result.summary\n"
        "def format_csv(result):\n"
        "    return result.summary\n"
    )
    result = run_slackers(tmp_path, _rc(), _slop())
    flagged = {v.symbol for v in result.violations}
    # `format_*` template covers all members → no slacker finding
    assert "result" not in flagged


def test_slackers_skips_strategy_family(tmp_path: Path):
    """color.py-style clone family is profile=strategy_family, not a real
    cluster for slackers purposes."""
    (tmp_path / "color.py").write_text(
        "def red(text): return f'r:{text}'\n"
        "def green(text): return f'g:{text}'\n"
        "def yellow(text): return f'y:{text}'\n"
        "def blue(text): return f'b:{text}'\n"
    )
    result = run_slackers(tmp_path, _rc(), _slop())
    flagged = {v.symbol for v in result.violations}
    # strategy_family profile excluded from slackers checks
    assert "text" not in flagged


def test_slackers_threshold_configurable(tmp_path: Path):
    """max_coverage parameter tunes the firing threshold."""
    (tmp_path / "f.py").write_text(
        "def calculate_invoice(customer):\n"
        "    return customer.lines\n"
        "def calculate_eligibility(customer):\n"
        "    return customer.tier\n"
        "def serialize_audit(customer):\n"
        "    return customer.id\n"
        "def fetch_history(customer):\n"
        "    return customer.id\n"
    )
    # With max_coverage=0.30 (default), the cluster has some `calculate_*`
    # template coverage; might fire or not depending. Test that
    # max_coverage=0.0 never fires (no cluster has 0% coverage).
    result = run_slackers(tmp_path, _rc(max_coverage=0.0), _slop())
    flagged = {v.symbol for v in result.violations}
    assert "customer" not in flagged
