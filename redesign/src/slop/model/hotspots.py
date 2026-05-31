"""Hotspots — churn x complexity per file (Tornhill 2015).

Joins per-file cyclomatic complexity (the module aggregate) with git numstat
churn (LOC delta over a window — the agentic-era proxy: one commit can dump 400
lines, so commit-count alone is noisy). 75th-percentile cutoffs on both axes
classify the quadrant; with < 8 ranked files the classifier abstains
(``insufficient_data``). Returns ``[]`` when ``root`` is not a git repo.
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from ..component.identity import ComponentKind
from ..component.metrics import Hotspot

_DEFAULT_WINDOW = "14 days ago"   # tuned for agentic code generation
_MIN_RANKED = 8


def hotspots(corpus: Any, *, since: str = _DEFAULT_WINDOW) -> list[Hotspot]:
    root = corpus.root
    repo_root = _repo_root(root)
    if repo_root is None:
        return []
    churn = _git_numstat(root, since)
    if churn is None:
        return []

    # Per-file complexity (module aggregate), keyed repo-relative.
    complexity: dict[str, int] = {}
    for mod in _modules(corpus):
        if not mod.files:
            continue
        rel = _repo_relative(mod.files[0], repo_root)
        if rel is not None:
            complexity[rel] = complexity.get(rel, 0) + mod.cyclomatic()

    files = sorted(set(complexity) | set(churn))
    rows = [(f, complexity.get(f, 0), churn.get(f, 0)) for f in files]
    if len(rows) < _MIN_RANKED:
        return [Hotspot(path=f, churn=c, complexity=x, quadrant="insufficient_data") for f, x, c in rows]

    ccx_cut = _p75([x for _f, x, _c in rows])
    churn_cut = _p75([c for _f, _x, c in rows])
    out: list[Hotspot] = []
    for f, x, c in rows:
        hi_x, hi_c = x >= ccx_cut, c >= churn_cut
        quadrant = (
            "hotspot" if hi_x and hi_c
            else "stable_complex" if hi_x
            else "churning_simple" if hi_c
            else "calm"
        )
        out.append(Hotspot(path=f, churn=c, complexity=x, quadrant=quadrant))
    out.sort(key=lambda h: (-(h.churn * h.complexity), h.path))
    return out


def _repo_root(root: Path) -> Path | None:
    try:
        r = subprocess.run(["git", "-C", str(root), "rev-parse", "--show-toplevel"],
                           capture_output=True, text=True, timeout=15)
        return Path(r.stdout.strip()) if r.returncode == 0 and r.stdout.strip() else None
    except Exception:
        return None


def _git_numstat(root: Path, since: str) -> dict[str, int] | None:
    try:
        r = subprocess.run(
            ["git", "-C", str(root), "log", "--no-merges", "--since", since,
             "--numstat", "--format=", "--", str(Path(root).resolve())],
            capture_output=True, text=True, timeout=30,
        )
        if r.returncode != 0:
            return None
    except Exception:
        return None
    churn: dict[str, int] = {}
    for line in r.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        ins, dels, path = parts
        delta = (int(ins) if ins.isdigit() else 0) + (int(dels) if dels.isdigit() else 0)
        churn[path] = churn.get(path, 0) + delta
    return churn


def _repo_relative(path: Path, repo_root: Path) -> str | None:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return None


def _p75(values: list[int]) -> int:
    if not values:
        return 0
    s = sorted(values)
    return s[min(len(s) - 1, int(0.75 * (len(s) - 1)))]


def _modules(component: Any):
    if component.KIND == ComponentKind.MODULE:
        yield component
        return
    for ch in component.children():
        yield from _modules(ch)
