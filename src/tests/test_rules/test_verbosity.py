"""Tests for lexical.verbosity rule and identifier splitting."""

from __future__ import annotations

from pathlib import Path

from slop._lexical.identifier_tokens import (
    identifier_token_kernel,
    split_identifier,
)
from slop.models import RuleConfig, SlopConfig
from slop.rules.verbosity import run_verbosity


def test_split_snake_case():
    assert split_identifier("my_func_name") == ["my", "func", "name"]


def test_split_camel_case():
    assert split_identifier("processDataFrame") == ["process", "Data", "Frame"]


def test_split_upper_camel_acronym():
    assert split_identifier("HTTPClient") == ["HTTP", "Client"]


def test_split_single_char():
    assert split_identifier("x") == ["x"]


def test_split_dunder():
    assert split_identifier("__init__") == ["init"]


def test_split_mixed():
    assert split_identifier("parseHTTPResponse") == ["parse", "HTTP", "Response"]


def test_split_digits_stripped():
    assert split_identifier("node2vec") == ["node", "vec"]


def test_rule_pass_concise_names(tmp_path: Path):
    (tmp_path / "a.py").write_text(
        "def compute_sum(values, scale):\n"
        "    result = sum(values) * scale\n"
        "    return result\n"
    )
    rc = RuleConfig(enabled=True, severity="warning",
                    params={"max_mean_tokens": 3.0, "min_identifiers": 3})
    result = run_verbosity(tmp_path, rc, SlopConfig(root=str(tmp_path)))
    assert result.status == "pass"
    assert result.violations == []


def test_rule_fail_verbose_names(tmp_path: Path):
    # Egregiously long names
    (tmp_path / "a.py").write_text(
        "def calculate_total_aggregated_value_with_scaling(input_data_collection, scaling_factor_parameter):\n"
        "    calculated_result_value_variable_with_extra_context = sum(input_data_collection) * scaling_factor_parameter\n"
        "    return calculated_result_value_variable_with_extra_context\n"
    )
    rc = RuleConfig(enabled=True, severity="warning",
                    params={"max_mean_tokens": 3.0, "min_identifiers": 3})
    result = run_verbosity(tmp_path, rc, SlopConfig(root=str(tmp_path)))
    assert result.status == "fail"
    assert len(result.violations) >= 1
    v = result.violations[0]
    assert v.rule == "lexical.verbosity"
    assert v.value > 3.0
