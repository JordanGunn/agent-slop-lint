"""``slop.config`` — configuration domain.

Owns the file-shape of slop's configuration: the top-level ``Config``
object, the ``Waiver`` record, the TOML loader that walks upward from
CWD looking for ``.slop.toml`` / ``pyproject.toml[tool.slop]``, and the
versioned JSON Schema asset under ``schema/``.

Rule-domain types (``Rule``, ``Severity``, ``Tag``, ``Scope``)
deliberately do not live here — they live in ``slop.linter`` because
they describe rule settings, not config-file shape. A config file
populates them; it does not own their semantics.
"""
from __future__ import annotations

from . import schema
from .config import Config, Waiver
from .loader import load_config

__all__ = ["Config", "Waiver", "load_config", "schema"]
