"""Re-export shim — metric result records moved to ``slop.metrics.structural.records``.

The records (Halstead/CK/Martin/clone/hotspot/… result types) are *measurements*, so
they now live with the metric views in ``metrics/structural``. This module re-exports
them so existing ``from ..component.metrics import …`` sites are unchanged during the
scope-layer migration. (Retired once those sites move off the entities at the sever.)
"""
from __future__ import annotations

from ..metrics.structural.records import (
    CallIsland,
    CKMetrics,
    CloneCluster,
    DependencyCycle,
    HalsteadProfile,
    Hotspot,
    ImportDecl,
    MagicLiteral,
    Orphan,
    PackageMetrics,
    ParameterMutation,
    RedundancyPair,
    SentinelParameter,
)

__all__ = [
    "HalsteadProfile",
    "MagicLiteral",
    "ParameterMutation",
    "SentinelParameter",
    "CKMetrics",
    "PackageMetrics",
    "RedundancyPair",
    "CloneCluster",
    "CallIsland",
    "Orphan",
    "Hotspot",
    "DependencyCycle",
    "ImportDecl",
]
