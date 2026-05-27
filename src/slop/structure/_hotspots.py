"""Hotspots compute — growth-weighted complexity scoring per file.

Composes per-file cyclomatic complexity (aggregated from the
``Structure`` view) with git numstat history to produce
``FileHotspot`` records. Tornhill 2015 churn-weighted complexity with
the v2.0 LOC-delta churn proxy (agentic-era tuning: a single commit
can dump 400 lines, so commit count alone is a noisy proxy).

Quadrant cutoffs use the 75th percentile on both axes (sum_ccx and
loc_delta). When fewer than 8 files have enough commits for ranking,
the classifier abstains and emits ``insufficient_data``.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from slop.structure._git import NumstatCommitRecord, git_log_numstat
from slop.structure.records import FileHotspot

if TYPE_CHECKING:
    from slop.structure.view import Structure


_EMPTY_QUADRANT_COUNTS: dict[str, int] = {
    "hotspot": 0,
    "stable_complex": 0,
    "churning_simple": 0,
    "calm": 0,
    "insufficient_data": 0,
}


def _empty_quadrant_counts() -> dict[str, int]:
    return dict(_EMPTY_QUADRANT_COUNTS)


def _normalize_since(since: str | None) -> str | None:
    """Convert ``'all'`` / empty / ``'unbounded'`` to ``None`` for git."""
    if since is None:
        return None
    trimmed = since.strip().lower()
    if trimmed in ("", "all", "unbounded"):
        return None
    return since


def _subdir_prefix(root: Path, repo_root: Path) -> str:
    """Compute the repo-root-relative prefix for files under ``root``."""
    root_resolved = root.resolve()
    repo_resolved = repo_root.resolve()
    if root_resolved == repo_resolved:
        return ""
    rel = root_resolved.relative_to(repo_resolved)
    return rel.as_posix()


def _scope_commits_to_prefix(
    commits: tuple[NumstatCommitRecord, ...], prefix: str,
) -> list[NumstatCommitRecord]:
    """Filter a commit list to files under the given repo-relative prefix."""
    if not prefix:
        return list(commits)
    prefix_with_slash = prefix + "/"
    scoped: list[NumstatCommitRecord] = []
    for c in commits:
        kept = tuple(
            f for f in c.files
            if f.file == prefix or f.file.startswith(prefix_with_slash)
        )
        if kept:
            scoped.append(NumstatCommitRecord(
                commit_hash=c.commit_hash,
                author_date=c.author_date,
                files=kept,
                parent_count=c.parent_count,
            ))
    return scoped


@dataclass
class _FileChurnAccum:
    insertions: int = 0
    deletions: int = 0
    commit_count: int = 0
    dates: list[str] = field(default_factory=list)


@dataclass
class _FileCCX:
    """Per-file CCX aggregation pulled from a Structure view."""
    abs_path: Path
    sum_ccx: int
    max_ccx: int
    language: str


def _aggregate_file_ccx(structure: Structure) -> dict[Path, _FileCCX]:
    """Bucket cyclomatic complexity by source file."""
    buckets: dict[Path, _FileCCX] = {}
    for c in structure.callables():
        ccx = structure.cyclomatic(c)
        path = Path(c.path)
        language = structure.language_for(c) or "unknown"
        existing = buckets.get(path)
        if existing is None:
            buckets[path] = _FileCCX(
                abs_path=path, sum_ccx=ccx, max_ccx=ccx, language=language,
            )
        else:
            existing.sum_ccx += ccx
            if ccx > existing.max_ccx:
                existing.max_ccx = ccx
    return buckets


def _percentile_cutoff(values: list[int], percentile: float) -> int:
    if not values:
        return 0
    n = len(values)
    idx = max(0, math.ceil(percentile * n) - 1)
    return sorted(values)[idx]


def _classify(
    rows: list[dict], percentile: float,
) -> tuple[list[dict], dict[str, int]]:
    """Assign a ``quadrant`` to each row; return counts."""
    counts = _empty_quadrant_counts()
    if len(rows) < 8:
        for r in rows:
            r["quadrant"] = "insufficient_data"
            counts["insufficient_data"] += 1
        return rows, counts

    p_ccx = _percentile_cutoff([r["sum_ccx"] for r in rows], percentile)
    p_churn = _percentile_cutoff([r["loc_delta"] for r in rows], percentile)
    for r in rows:
        high_ccx = r["sum_ccx"] >= p_ccx
        high_churn = r["loc_delta"] >= p_churn
        if high_ccx and high_churn:
            q = "hotspot"
        elif high_ccx:
            q = "stable_complex"
        elif high_churn:
            q = "churning_simple"
        else:
            q = "calm"
        r["quadrant"] = q
        counts[q] += 1
    return rows, counts


@dataclass(frozen=True)
class HotspotsComputeResult:
    """Output of ``compute_hotspots`` — files + summary metadata."""
    files: tuple[FileHotspot, ...]
    quadrant_counts: dict[str, int]
    window_since: str
    window_until: str
    total_commits_analyzed: int
    files_analyzed: int
    errors: tuple[str, ...]


def compute_hotspots(
    structure: Structure,
    root: Path,
    *,
    since: str | None = "14 days ago",
    until: str | None = None,
    min_commits: int = 2,
    hotspot_percentile: float = 0.75,
) -> HotspotsComputeResult:
    """Compute per-file growth-weighted complexity hotspots.

    Args:
        structure: Parsed corpus view (provides per-file CCX).
        root: Repository root or any path inside the repo.
        since: Git log window start. ``"14 days ago"`` by default (agentic-
            era tuning). Use ``"all"`` for an unbounded window.
        until: Git log window end.
        min_commits: Exclude files with fewer than this many commits in
            the window.
        hotspot_percentile: Cutoff for quadrant classification (default
            0.75 = top 25% on each axis).
    """
    errors: list[str] = []
    display_since = since if since is not None else "unbounded"
    display_until = until if until is not None else ""

    git_result = git_log_numstat(
        root, since=_normalize_since(since), until=until, include_merges=False,
    )
    if not git_result.ok or git_result.repo_root is None:
        errors.extend(f"git: {e}" for e in git_result.errors)
        if git_result.repo_root is None and git_result.ok:
            errors.append("git: repo_root resolution failed despite ok=True")
        return HotspotsComputeResult(
            files=(), quadrant_counts=_empty_quadrant_counts(),
            window_since=display_since, window_until=display_until,
            total_commits_analyzed=0, files_analyzed=0,
            errors=tuple(errors),
        )
    errors.extend(f"git: {e}" for e in git_result.errors)

    repo_root = git_result.repo_root
    try:
        prefix = _subdir_prefix(root, repo_root)
    except ValueError:
        errors.append(f"root {root} is not inside repo_root {repo_root}")
        return HotspotsComputeResult(
            files=(), quadrant_counts=_empty_quadrant_counts(),
            window_since=display_since, window_until=display_until,
            total_commits_analyzed=0, files_analyzed=0,
            errors=tuple(errors),
        )
    scoped_commits = _scope_commits_to_prefix(git_result.commits, prefix)

    ccx_by_path = _aggregate_file_ccx(structure)

    # Key everything by repo-root-relative path (forward slash).
    ccx_by_repo_rel: dict[str, _FileCCX] = {}
    for abs_path, info in ccx_by_path.items():
        try:
            rel = abs_path.resolve().relative_to(repo_root).as_posix()
        except ValueError:
            continue
        ccx_by_repo_rel[rel] = info

    churn: dict[str, _FileChurnAccum] = {}
    for c in scoped_commits:
        for fcr in c.files:
            acc = churn.setdefault(fcr.file, _FileChurnAccum())
            acc.insertions += fcr.insertions
            acc.deletions += fcr.deletions
            acc.commit_count += 1
            acc.dates.append(c.author_date)

    rows: list[dict] = []
    for repo_rel, info in ccx_by_repo_rel.items():
        if info.sum_ccx == 0:
            continue
        acc = churn.get(repo_rel)
        if acc is None or acc.commit_count < min_commits:
            continue
        loc_delta = acc.insertions - acc.deletions
        loc_delta_clamped = max(0, loc_delta)
        score = float(info.sum_ccx * loc_delta_clamped)
        sorted_dates = sorted(acc.dates)
        rows.append({
            "file": repo_rel,
            "path": str(info.abs_path),
            "language": info.language,
            "sum_ccx": info.sum_ccx,
            "max_ccx": info.max_ccx,
            "loc_delta": loc_delta,
            "loc_insertions": acc.insertions,
            "loc_deletions": acc.deletions,
            "commit_count": acc.commit_count,
            "first_seen": sorted_dates[0][:10],
            "last_seen": sorted_dates[-1][:10],
            "hotspot_score": score,
        })

    rows.sort(key=lambda r: (-r["hotspot_score"], -r["sum_ccx"], -r["loc_delta"], r["file"]))
    rows, quadrant_counts = _classify(rows, hotspot_percentile)

    files = tuple(
        FileHotspot(
            file=r["file"], path=r["path"], language=r["language"],
            sum_ccx=r["sum_ccx"], max_ccx=r["max_ccx"],
            loc_delta=r["loc_delta"],
            loc_insertions=r["loc_insertions"],
            loc_deletions=r["loc_deletions"],
            commit_count=r["commit_count"],
            first_seen=r["first_seen"], last_seen=r["last_seen"],
            hotspot_score=r["hotspot_score"], quadrant=r["quadrant"],
        )
        for r in rows
    )

    return HotspotsComputeResult(
        files=files,
        quadrant_counts=quadrant_counts,
        window_since=display_since,
        window_until=display_until,
        total_commits_analyzed=len(scoped_commits),
        files_analyzed=len(files),
        errors=tuple(errors),
    )
