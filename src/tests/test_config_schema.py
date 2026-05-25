"""Drift guard: the committed v1.json must stay in sync with the Python defaults.

The JSON Schema asset under ``slop/config/schema/v1.json`` is the
declared source of truth for the config-file shape. The Python-side
``Config`` dataclass and ``DEFAULT_RULE_CONFIGS`` dict are what the
loader actually populates. Either side moving without the other being
updated is the failure mode this test catches.
"""
from __future__ import annotations

from dataclasses import fields

from slop.config import Config, schema
from slop.config.loader import DEFAULT_RULE_CONFIGS


def test_top_level_config_fields_present_in_schema() -> None:
    v1 = schema.load("v1")
    declared = set(v1["properties"].keys())
    # config_path is loader-populated, not user-supplied — exempt
    expected = {f.name for f in fields(Config)} - {"config_path"}
    missing = expected - declared
    assert not missing, (
        f"Config dataclass fields missing from v1.json properties: {sorted(missing)}"
    )


def test_every_default_rule_present_in_schema() -> None:
    v1 = schema.load("v1")
    declared = set(v1["properties"]["rules"]["properties"].keys())
    expected = set(DEFAULT_RULE_CONFIGS.keys())
    missing = expected - declared
    assert not missing, (
        f"DEFAULT_RULE_CONFIGS keys missing from v1.json rules.properties: "
        f"{sorted(missing)}"
    )


def test_no_orphan_rules_in_schema() -> None:
    """v1.json should not declare rules that no longer exist in defaults."""
    v1 = schema.load("v1")
    declared = set(v1["properties"]["rules"]["properties"].keys())
    expected = set(DEFAULT_RULE_CONFIGS.keys())
    orphans = declared - expected
    assert not orphans, (
        f"v1.json declares rules absent from DEFAULT_RULE_CONFIGS: {sorted(orphans)}"
    )
