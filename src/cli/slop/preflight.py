"""Preflight system-dependency check.

slop's rules shell out to ``fd``, ``git``, and ``rg``. When a binary is
missing, the kernel silently returns zero files — which the human
formatter renders as ``✓ clean``. This module resolves that by checking
required binaries up-front and failing fast with a clear block that
points at install instructions.

The required-binary set is rule-driven:
- ``fd`` is always required (every file-discovery kernel uses it).
- ``git`` is required when the ``hotspots`` rule is enabled.
- ``rg`` is required when the ``orphans`` rule is enabled.
"""

from __future__ import annotations

from dataclasses import dataclass

from slop._util.doctor import check_tool
from slop.models import SlopConfig


@dataclass(frozen=True)
class MissingBinary:
    """A system binary required by an enabled rule that was not found."""

    name: str                # canonical tool name (e.g. "fd")
    rules: tuple[str, ...]   # slop rules that need it (e.g. ("complexity.*", ...))
    install: str             # install hint URL or command


def required_binaries(config: SlopConfig) -> dict[str, tuple[str, ...]]:
    """Return {binary_name: (rules_that_need_it, ...)} for enabled rules.

    ``fd`` is always listed because all file-discovery kernels use it.
    """
    # fd: universal. Attributed to "file discovery" for readability rather
    # than enumerating every rule that indirectly depends on it.
    needed: dict[str, list[str]] = {"fd": ["file discovery"]}

    hotspots = config.rules.get("hotspots")
    if hotspots is None or hotspots.enabled:
        needed.setdefault("git", []).append("hotspots")

    orphans = config.rules.get("orphans")
    if orphans is not None and orphans.enabled:
        needed.setdefault("rg", []).append("orphans")

    return {k: tuple(v) for k, v in needed.items()}


def check_required_binaries(config: SlopConfig) -> list[MissingBinary]:
    """Check every binary required by the enabled rule set.

    Returns the list of missing binaries (empty when everything is present).
    """
    missing: list[MissingBinary] = []
    for name, rules in required_binaries(config).items():
        result = check_tool(name)
        if not result.get("available", False):
            missing.append(
                MissingBinary(
                    name=name,
                    rules=rules,
                    install=result.get("install", ""),
                )
            )
    return missing
