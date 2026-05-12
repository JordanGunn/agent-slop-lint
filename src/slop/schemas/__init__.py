"""``slop.schemas`` — IO schema generators.

JSON Schemas describing the boundaries between slop and external
consumers: the config file format (``config.py``) and (future)
output JSON format (``output.py``).

Each schema module exposes a ``generate() -> dict`` function. The
``slop schema`` CLI command is a thin wrapper around these.
"""
from __future__ import annotations

from . import config

__all__ = ["config"]
