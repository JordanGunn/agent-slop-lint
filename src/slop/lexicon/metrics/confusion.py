"""lexical.confusion — file holds multiple distinct lexicons.

A file is "confused" when it contains multiple cohesive first-
parameter clusters that each look like a missing class. The file is
doing the work of multiple cohesive units sharing a namespace; the
canonical refactor is to split it along receiver boundaries.

Adapts Lanza & Marinescu's (2006) detection-strategy framework from
OO classes to module-level free-function code. PoC reference:
``scripts/research/composition_poc_v2/poc7_lanza_marinescu.py``.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from slop.linter.rule_config import RuleConfig
from slop.config import Config
from slop.linter.slop import Slop
from slop.linter.types import RuleResult
from slop.tree.records import CallableKind
from slop.linter.tags import Tag
from slop.linter.types import RuleDefinition

if TYPE_CHECKING:
    from slop.lexicon.view import Lexicon


def _derive_root(lexicon: Lexicon, slop_config: Config) -> Path:
    """Prefer slop_config.root when explicitly set; otherwise fall back
    to the longest common directory across the lexicon's parses."""
    if slop_config.root and slop_config.root != ".":
        return Path(slop_config.root).expanduser().resolve()
    paths = [p.path for p in lexicon._parses]  # noqa: SLF001
    if paths:
        common = Path(os.path.commonpath([str(p) for p in paths]))
        return common.parent if common.is_file() else common
    if slop_config.root:
        return Path(slop_config.root).expanduser().resolve()
    return Path.cwd()


def _functions_per_file(lexicon: Lexicon, root: Path) -> dict[str, int]:
    """Count emittable functions per file-relative path."""
    counts: dict[str, int] = {}
    for c in lexicon.callables():
        if c.kind == CallableKind.LAMBDA:
            continue
        try:
            rel = str(c.path.relative_to(root))
        except ValueError:
            rel = str(c.path)
        counts[rel] = counts.get(rel, 0) + 1
    return counts


def run_confusion(
    lexicon: Lexicon, rule_config: RuleConfig, slop_config: Config,
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

    clusters = lexicon.first_param_clusters(
        min_cluster=min_cluster_size,
        exempt_names=exempt_names,
        root=root,
    )

    # Group file-scope clusters by file. Package/root-scope clusters
    # are irrelevant for the file-level rule.
    by_file: dict[str, list] = {}
    for cluster in clusters:
        if cluster.scope_kind != "file":
            continue
        by_file.setdefault(cluster.scope, []).append(cluster)

    functions_per_file = _functions_per_file(lexicon, root)
    files_searched = len(functions_per_file)
    functions_analyzed = sum(functions_per_file.values())

    violations: list[Slop] = []
    for file, file_clusters in by_file.items():
        n_functions = functions_per_file.get(file, 0)
        if n_functions < min_functions:
            continue
        if len(file_clusters) < min_clusters:
            continue
        strong_receivers = [
            c.parameter_name for c in file_clusters
            if c.profile_label == "missing_class"
        ]
        if len(strong_receivers) < min_strong_receivers:
            continue
        first_cluster = file_clusters[0]
        line = first_cluster.members[0][2] if first_cluster.members else 1
        cluster_tuples = [
            (c.parameter_name, len(c.members), c.profile_label)
            for c in file_clusters
        ]
        cluster_summary = ", ".join(
            f"`{p}` ({n}, {label})" for p, n, label in cluster_tuples
        )
        receivers_repr = ", ".join(f"`{r}`" for r in strong_receivers)
        violations.append(Slop(
            rule="lexical.confusion",
            file=file,
            line=line,
            symbol=file,
            message=(
                f"`{file}` holds {n_functions} functions "
                f"clustering on {len(file_clusters)} distinct receivers "
                f"({cluster_summary}). "
                f"{len(strong_receivers)} are strong missing-class "
                f"candidates ({receivers_repr}). The file is doing the work "
                f"of multiple cohesive units; split along receiver boundaries."
            ),
            severity=severity,
            value=len(strong_receivers),
            threshold=min_strong_receivers,
            metadata={
                "function_count": n_functions,
                "clusters": [
                    {"param": p, "members": n, "profile": label}
                    for p, n, label in cluster_tuples
                ],
                "strong_receivers": strong_receivers,
            },
        ))

    return RuleResult(
        rule="lexical.confusion",
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "files_searched": files_searched,
            "functions_checked": functions_analyzed,
            "candidate_files": len(by_file),
            "violation_count": len(violations),
        },
        errors=[],
    )

RULE = RuleDefinition(
    name=Tag.CONFUSION.key,
    category=Tag.CONFUSION.key,
    description='File holds multiple distinct strong-receiver clusters (Lanza & Marinescu Extract Class)',
    default_severity='warning',
    default_enabled=True,
    threshold_label='≥ 2 clusters × ≥ 3 members',
    run=run_confusion,
)
