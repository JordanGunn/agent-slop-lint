"""Hotspots: churn x complexity per file (Tornhill 2015).

Churn is lines added plus lines removed. The window is a span of revisions, not of
calendar time, because an agent can change a repository more in one prompt than a person
does in a month:

- the commits in ``REV..HEAD`` (``since=REV``), or the last ``last`` commits;
- plus every uncommitted change: tracked files against ``HEAD``, and untracked files
  that ``.gitignore`` does not ignore (counted as all lines added).

``since="HEAD"`` (or ``last=0``) therefore means the changes made since the last commit.
Complexity is the file's summed cyclomatic complexity. Only files the corpus carved are
ranked. Raises ``ValueError`` outside a git work tree or in one with no commits.
"""
from __future__ import annotations

import subprocess
from collections import Counter
from pathlib import Path
from typing import Any, Iterator

from .complexity import cyclomatic as _cyclomatic
from .records import Hotspot

DEFAULT_LAST = 10


def hotspots(corpus: Any, *, since: str | None = None, last: int = DEFAULT_LAST) -> list[Hotspot]:
    """Files with churn in the window, hottest (churn x complexity) first."""
    repo = Path(_git(corpus.root, "rev-parse", "--show-toplevel").strip())
    if _git(repo, "rev-parse", "--verify", "--quiet", "HEAD", check=False) is None:
        raise ValueError("the repository has no commits")
    churn = _churn(repo, _span(repo, since, last))

    rows: list[Hotspot] = []
    for mod in corpus._iter_modules():
        if not mod.files:
            continue
        rel = _repo_relative(mod.files[0], repo)
        if rel is None or not churn.get(rel):
            continue
        rows.append(Hotspot(path=rel, churn=churn[rel], complexity=_module_cyclomatic(mod),
                            locus=mod.id))
    rows.sort(key=lambda h: (-(h.churn * h.complexity), h.path))
    return rows


def _span(repo: Path, since: str | None, last: int) -> str:
    """The ``git log`` revision argument for the committed part of the window."""
    if since is not None:
        if _git(repo, "rev-parse", "--verify", "--quiet", f"{since}^{{commit}}", check=False) is None:
            raise ValueError(f"unknown revision: {since}")
        return f"{since}..HEAD"
    if last < 0:
        raise ValueError("last must be 0 or more")
    if _git(repo, "rev-parse", "--verify", "--quiet", f"HEAD~{last}", check=False) is None:
        return "HEAD"                       # fewer than `last` commits: the whole history
    return f"HEAD~{last}..HEAD"


def _churn(repo: Path, span: str) -> Counter:
    churn: Counter = Counter()
    committed = _git(repo, "log", "--no-merges", "--no-renames", "--numstat", "-z",
                     "--format=", span)
    uncommitted = _git(repo, "diff", "HEAD", "--no-renames", "--numstat", "-z")
    for out in (committed, uncommitted):
        for path, lines in _numstat(out):
            churn[path] += lines
    for path in _git(repo, "ls-files", "-z", "--others", "--exclude-standard").split("\0"):
        if path:
            churn[path] += _line_count(repo / path)
    return churn


def _numstat(out: str) -> Iterator[tuple[str, int]]:
    """``added<TAB>removed<TAB>path`` entries; binary files (``-``) carry no line count."""
    for entry in out.split("\0"):
        parts = entry.strip("\n").split("\t", 2)
        if len(parts) == 3 and parts[0].isdigit() and parts[1].isdigit():
            yield parts[2], int(parts[0]) + int(parts[1])


def _line_count(path: Path) -> int:
    try:
        data = path.read_bytes()
    except OSError:
        return 0
    if b"\0" in data:
        return 0
    return data.count(b"\n") + (1 if data and not data.endswith(b"\n") else 0)


def _git(directory: Path, *args: str, check: bool = True) -> str | None:
    """Run git in ``directory``; return stdout, or None when ``check`` is off and git fails."""
    try:
        done = subprocess.run(["git", "-C", str(directory), *args],
                              capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError(f"cannot run git: {exc}") from exc
    if done.returncode != 0:
        if not check:
            return None
        if args[0] == "rev-parse" and "--show-toplevel" in args:
            raise ValueError(f"not a git work tree: {directory}")
        raise ValueError(f"git {args[0]} failed: {done.stderr.strip()}")
    return done.stdout


def _repo_relative(path: Path, repo: Path) -> str | None:
    try:
        return path.resolve().relative_to(repo.resolve()).as_posix()
    except ValueError:
        return None


def _module_cyclomatic(mod: Any) -> int:
    """Summed cyclomatic complexity of the module's callables."""
    return sum(_cyclomatic(c._ast_node(), c._grammar) for c in mod._iter_callables())
