"""Confusion kernel — file-level Extract Class detection.

Adapts the Lanza & Marinescu (2006) detection-strategy framework
from class-level (their book targets OO classes) to module-level
(slop's Python corpus is mostly free-function modules).

A file is a confusion candidate when:

- It contains ≥ ``min_functions`` functions (sufficient material
  to split)
- Those functions cluster into ≥ ``min_clusters`` distinct
  first-parameter groups, each ≥ ``min_cluster_size`` (the file
  is doing multiple things)
- ≥ ``min_strong_receivers`` of those clusters are
  ``missing_class`` per the imposters profile (each is a
  meaningful receiver, not a generic param)

The reading: this file is the work of multiple cohesive units
sharing a namespace. Split along receiver boundaries — each
strong-receiver cluster becomes its own module (or class).

Reference: Lanza & Marinescu (2006), Marinescu (2004); v2 PoC
``scripts/research/composition_poc_v2/poc7_lanza_marinescu.py``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from slop._lexical.imposters import imposters_kernel


@dataclass
class ConfusionFile:
    """One file flagged as a confusion candidate."""
    file: str
    function_count: int
    clusters: list[tuple[str, int, str]]   # (param_name, member_count, profile_label)
    strong_receivers: list[str]            # parameter names with missing_class profile
    line: int = 1                          # anchor line (first cluster's first member)


@dataclass
class ConfusionResult:
    files: list[ConfusionFile] = field(default_factory=list)
    files_searched: int = 0
    functions_analyzed: int = 0
    errors: list[str] = field(default_factory=list)


def confusion_kernel(
    root: Path,
    *,
    languages: list[str] | None = None,
    globs: list[str] | None = None,
    excludes: list[str] | None = None,
    hidden: bool = False,
    no_ignore: bool = False,
    min_functions: int = 5,
    min_clusters: int = 2,
    min_cluster_size: int = 3,
    min_strong_receivers: int = 2,
    exempt_names: frozenset[str] = frozenset(),
) -> ConfusionResult:
    """Detect files holding multiple distinct strong-receiver clusters.

    A file fires when it has many functions AND those functions
    split into multiple meaningful first-parameter clusters AND
    multiple of those clusters carry the ``missing_class``
    profile from the imposters kernel.
    """
    imposters = imposters_kernel(
        root,
        languages=languages, globs=globs, excludes=excludes,
        hidden=hidden, no_ignore=no_ignore,
        min_cluster=min_cluster_size, exempt_names=exempt_names,
    )

    # Group imposters clusters by file. The cluster's ``scope`` may
    # span more than one file at package/root scope, but for
    # confusion's file-level rule we only care about clusters whose
    # scope IS a file.
    by_file: dict[str, list] = {}
    for cluster in imposters.clusters:
        if cluster.scope_kind != "file":
            continue
        by_file.setdefault(cluster.scope, []).append(cluster)

    # Count functions per file. Re-enumerate (cheap) since imposters
    # only retains cluster members, not all functions.
    from slop._lexical._naming import enumerate_functions
    functions_per_file: dict[str, int] = {}
    files_seen: set[str] = set()
    total = 0
    for ctx in enumerate_functions(
        root, languages=languages, globs=globs, excludes=excludes,
        hidden=hidden, no_ignore=no_ignore,
    ):
        functions_per_file[ctx.file] = functions_per_file.get(ctx.file, 0) + 1
        files_seen.add(ctx.file)
        total += 1

    findings: list[ConfusionFile] = []
    for file, clusters in by_file.items():
        n_functions = functions_per_file.get(file, 0)
        if n_functions < min_functions:
            continue
        if len(clusters) < min_clusters:
            continue
        strong_receivers = [
            c.parameter_name for c in clusters
            if c.profile_label == "missing_class"
        ]
        if len(strong_receivers) < min_strong_receivers:
            continue
        # Anchor line: first cluster's first member's line
        first_cluster = clusters[0]
        line = first_cluster.members[0][2] if first_cluster.members else 1
        findings.append(ConfusionFile(
            file=file,
            function_count=n_functions,
            clusters=[
                (c.parameter_name, len(c.members), c.profile_label)
                for c in clusters
            ],
            strong_receivers=strong_receivers,
            line=line,
        ))

    return ConfusionResult(
        files=findings,
        files_searched=len(files_seen),
        functions_analyzed=total,
        errors=list(imposters.errors),
    )
