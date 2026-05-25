"""File-parsing primitive used by ``Tree.scan()``.

Wraps the tree-sitter parser API compat shim (pre/post 0.22). Returns
``(tree, content)`` on success or ``None`` on failure. The grammar is
loaded via ``slop.language.treesitter.load_language``.
"""
from __future__ import annotations

from pathlib import Path

import tree_sitter

from slop.language.treesitter import load_language


def parse_file(path: Path, language_name: str) -> tuple[object, bytes] | None:
    """Read ``path`` and parse it with the tree-sitter grammar for
    ``language_name``. ``None`` on grammar miss or parse failure."""
    tree_lang = load_language(language_name)
    if tree_lang is None:
        return None

    try:
        content = path.read_bytes()
    except OSError:
        return None

    try:
        try:
            parser = tree_sitter.Parser(tree_lang)
        except TypeError:
            parser = tree_sitter.Parser()
            parser.language = tree_lang  # type: ignore[assignment]
        tree = parser.parse(content)
    except Exception:
        return None

    return tree, content
