"""The bounded source text a question is about."""
from __future__ import annotations

from pathlib import Path

from ..contract import Excerpt

#: Longest excerpt. A longer span is cut here, and ``last_line`` says where.
MAX_LINES = 120


def excerpt(path: Path, root: Path, first_line: int, last_line: int) -> Excerpt:
    """Lines ``first_line`` through ``last_line`` (1-based, inclusive) of ``path``, labelled
    relative to ``root``. Cut at ``MAX_LINES``; a range past the end of the file is clipped."""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    last = min(last_line, first_line + MAX_LINES - 1, len(lines))
    try:
        label = path.relative_to(root).as_posix()
    except ValueError:
        label = path.as_posix()
    return Excerpt(path=label, first_line=first_line, last_line=last,
                   text="\n".join(lines[first_line - 1:last]))
