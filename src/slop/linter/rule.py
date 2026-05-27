"""Per-rule configuration — what the loader produces for each rule."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Rule:
    """Per-rule configuration extracted from the slop config file.

    ``enabled`` and ``severity`` are scalar; rule-specific tunables
    live in ``params`` (notably the ``thresholds`` sub-dict for the
    per-scope threshold dispatch pattern).
    """

    enabled: bool = True
    severity: str = "error"           # "error" | "warning" | "off"
    params: dict[str, Any] = field(default_factory=dict)
