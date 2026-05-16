"""lexical.confusion — file holds multiple distinct lexicons.

A file is "confused" when it contains multiple cohesive first-
parameter clusters that each look like a missing class. The file is
doing the work of multiple cohesive units sharing a namespace; the
canonical refactor is to split it along receiver boundaries.

Adapts Lanza & Marinescu's (2006) detection-strategy framework from
OO classes to module-level free-function code.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from slop._lexical.confusion import confusion_kernel
from slop.config.models import RuleConfig, SlopConfig
from slop.linter.slop import Slop
from slop.linter.types import RuleResult

if TYPE_CHECKING:
    from slop.lexicon.view import Lexicon


def _derive_root(lexicon, slop_config: SlopConfig) -> Path:
    """Prefer slop_config.root when explicitly set; otherwise fall back
    to the longest common directory across the lexicon's parses."""
    if slop_config.root and slop_config.root != ".":
        return Path(slop_config.root).expanduser().resolve()
    paths = [p.path for p in lexicon._parses]
    if paths:
        common = Path(os.path.commonpath([str(p) for p in paths]))
        return common.parent if common.is_file() else common
    if slop_config.root:
        return Path(slop_config.root).expanduser().resolve()
    return Path.cwd()


def run_confusion(
    lexicon: Lexicon, rule_config: RuleConfig, slop_config: SlopConfig,
) -> RuleResult:
    """Flag files that hold multiple distinct strong-receiver clusters."""
    min_functions = int(rule_config.params.get("min_functions", 5))
    min_clusters = int(rule_config.params.get("min_clusters", 2))
    min_cluster_size = int(rule_config.params.get("min_cluster_size", 3))
    min_strong_receivers = int(rule_config.params.get("min_strong_receivers", 2))
    raw_exempt = rule_config.params.get("exempt_names", ["self", "cls"])
    exempt_names = frozenset(raw_exempt) if raw_exempt else frozenset()
    severity = rule_config.severity
    root = _derive_root(lexicon, slop_config)

    result = confusion_kernel(
        root,
        languages=slop_config.languages or None,
        excludes=slop_config.exclude or None,
        min_functions=min_functions,
        min_clusters=min_clusters,
        min_cluster_size=min_cluster_size,
        min_strong_receivers=min_strong_receivers,
        exempt_names=exempt_names,
    )

    violations: list[Slop] = []
    for finding in result.files:
        cluster_summary = ", ".join(
            f"`{p}` ({n}, {label})" for p, n, label in finding.clusters
        )
        receivers_repr = ", ".join(f"`{r}`" for r in finding.strong_receivers)
        violations.append(Slop(
            rule="lexical.confusion",
            file=finding.file,
            line=finding.line,
            symbol=finding.file,
            message=(
                f"`{finding.file}` holds {finding.function_count} functions "
                f"clustering on {len(finding.clusters)} distinct receivers "
                f"({cluster_summary}). "
                f"{len(finding.strong_receivers)} are strong missing-class "
                f"candidates ({receivers_repr}). The file is doing the work "
                f"of multiple cohesive units; split along receiver boundaries."
            ),
            severity=severity,
            value=len(finding.strong_receivers),
            threshold=min_strong_receivers,
            metadata={
                "function_count": finding.function_count,
                "clusters": [
                    {"param": p, "members": n, "profile": label}
                    for p, n, label in finding.clusters
                ],
                "strong_receivers": list(finding.strong_receivers),
            },
        ))

    return RuleResult(
        rule="lexical.confusion",
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "files_searched": result.files_searched,
            "functions_checked": result.functions_analyzed,
            "candidate_files": len(result.files),
            "violation_count": len(violations),
        },
        errors=list(result.errors),
    )
