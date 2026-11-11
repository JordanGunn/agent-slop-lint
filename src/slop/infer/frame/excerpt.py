"""The bounded source text a question is about.

STUB: the signature is fixed; extraction is not built.
"""
from __future__ import annotations

from pathlib import Path

from ..contract import Excerpt


def excerpt(path: Path, root: Path, first_line: int, last_line: int) -> Excerpt:
    """The lines ``first_line`` through ``last_line`` of ``path``, labelled relative to ``root``."""
    raise NotImplementedError("infer.frame.excerpt.excerpt: designed, not built")
