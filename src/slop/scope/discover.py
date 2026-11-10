"""File discovery: which files under a root exist for slop to read.

Inside a git work tree the answer is git's own: tracked files plus untracked files that
``.gitignore`` does not ignore. Elsewhere it is every file under the root, minus ``.git``
metadata. ``exclude`` in the config is the one other filter; it is applied by the caller.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Iterator


def source_files(root: Path) -> Iterator[Path]:
    """Yield each file under ``root`` (``root`` itself if it is a file), in sorted order."""
    if root.is_file():
        yield root
        return
    listed = _git_files(root)
    if listed is None:
        listed = _walk(root)
    for rel in sorted(listed):
        path = root / rel
        if path.is_file():
            yield path


def _git_files(root: Path) -> list[str] | None:
    """Paths relative to ``root`` that git would consider, or None outside a work tree."""
    try:
        done = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            capture_output=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if done.returncode != 0:
        return None
    return [p for p in done.stdout.decode("utf-8", errors="replace").split("\0") if p]


def _walk(root: Path) -> list[str]:
    found: list[str] = []
    for directory, subdirs, names in os.walk(root):
        subdirs[:] = [d for d in subdirs if d != ".git"]
        base = Path(directory).relative_to(root)
        found.extend((base / name).as_posix() for name in names)
    return found
