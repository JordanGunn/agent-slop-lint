"""The bounded source text a question is about."""
from __future__ import annotations

from pathlib import Path

from ..contract import Excerpt
from .location import project_path

#: Longest excerpt. A longer span is cut here, and ``last_line`` says where.
MAX_LINES = 120


def excerpt(path: Path, root: Path, first_line: int, last_line: int) -> Excerpt:
    """Lines ``first_line`` through ``last_line`` (1-based, inclusive) of ``path``, labelled
    relative to the project ``root``. Cut at ``MAX_LINES``; a range past the end of the file is clipped."""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    last = min(last_line, first_line + MAX_LINES - 1, len(lines))
    return Excerpt(path=project_path(path, root), first_line=first_line, last_line=last,
                   text="\n".join(lines[first_line - 1:last]))
