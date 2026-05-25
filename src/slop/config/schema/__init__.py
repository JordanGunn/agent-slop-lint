"""Versioned JSON Schema assets for slop's config file.

Each version of the config file shape is committed as a literal JSON
Schema asset (``v1.json``, ``v2.json``, …) — the asset is the source
of truth, not a Python function. ``load(version)`` reads the asset off
disk via ``importlib.resources`` so it works equally well from a wheel
install or a source checkout.

The drift guard in ``tests/test_config_schema.py`` asserts the asset
and the Python ``Config`` / ``DEFAULT_RULE_CONFIGS`` defaults stay in
sync; CI fails if they diverge.
"""
from __future__ import annotations

import json
from importlib import resources
from typing import Any

LATEST = "v1"


def load(version: str = LATEST) -> dict[str, Any]:
    """Return the JSON Schema dict for the requested config version."""
    asset = resources.files(__name__).joinpath(f"{version}.json")
    return json.loads(asset.read_text(encoding="utf-8"))


__all__ = ["LATEST", "load"]
