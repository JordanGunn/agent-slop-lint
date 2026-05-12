"""Signature adapter — bridges (root, rc, sc) rule signature to (view, rc, sc).

Legacy rules accept a filesystem root; rules ported to v2 view-aware
form accept a Structure/Lexicon view. This shim ignores the view and
threads ``slop_config.root`` into the legacy-shape call. Used in
``rules/__init__.py`` to wrap legacy rule run functions in the v2
RuleDefinition ``run=`` slot.

Retires when each rule's logic moves natively onto its view (one
intent per rule; the legacy kernels under ``slop._structural/`` and
``slop._lexical/`` retire alongside).
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable as TypingCallable

from slop.config.models import RuleConfig, SlopConfig
from slop.linter.types import RuleResult


def legacy_v2_shim(
    legacy_run: TypingCallable[[Path, RuleConfig, SlopConfig], RuleResult],
) -> TypingCallable[[object, RuleConfig, SlopConfig], RuleResult]:
    """Adapt a legacy ``run(root, rc, sc)`` rule into a v2 ``run(view, rc, sc)``."""
    def _shim(view: object, rc: RuleConfig, sc: SlopConfig) -> RuleResult:
        del view  # contract requires the slot; legacy kernel doesn't use it
        root = Path(sc.root).expanduser().resolve()
        return legacy_run(root, rc, sc)
    return _shim
