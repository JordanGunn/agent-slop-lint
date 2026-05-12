"""Config-file JSON Schema generator.

Builds a JSON Schema describing the structure of ``.slop.toml`` from
``DEFAULT_RULE_CONFIGS``. Consumed by the ``slop schema`` CLI command
and by any agent/IDE wanting to validate config files before applying.
"""
from __future__ import annotations

from typing import Any


def generate() -> dict[str, Any]:
    """Return the JSON Schema for the slop config file."""
    from slop.config import DEFAULT_RULE_CONFIGS

    return {
        "type": "object",
        "properties": {
            "root": {"type": "string", "default": "."},
            "languages": {"type": "array", "items": {"type": "string"}, "default": []},
            "exclude": {"type": "array", "items": {"type": "string"}, "default": []},
            "rules": {
                "type": "object",
                "properties": {
                    category: {
                        "type": "object",
                        "properties": {
                            k: {"default": v} for k, v in defaults.items()
                        },
                    }
                    for category, defaults in DEFAULT_RULE_CONFIGS.items()
                },
            },
        },
    }
