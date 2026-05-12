"""Shared tree-sitter utilities for AST-aware skills (query, sed)."""

from __future__ import annotations

import importlib
from pathlib import Path

import tree_sitter

# Language name → tree-sitter package name
GRAMMAR_MAP: dict[str, str] = {
    "python": "tree_sitter_python",
    "javascript": "tree_sitter_javascript",
    "typescript": "tree_sitter_typescript",
    "rust": "tree_sitter_rust",
    "go": "tree_sitter_go",
    "java": "tree_sitter_java",
    "c": "tree_sitter_c",
    "cpp": "tree_sitter_cpp",
    "ruby": "tree_sitter_ruby",
    "bash": "tree_sitter_bash",
    "c_sharp": "tree_sitter_c_sharp",
    "julia": "tree_sitter_julia",
}

# Extension → language name
EXT_LANGUAGE_MAP: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".rs": "rust",
    ".go": "go",
    ".java": "java",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".hxx": "cpp",
    ".rb": "ruby",
    ".sh": "bash",
    ".bash": "bash",
    ".cs": "c_sharp",
    ".jl": "julia",
}

# Cache for loaded Language objects
_LANGUAGE_CACHE: dict[str, object] = {}


def detect_language(path: Path, override: str | None = None) -> str | None:
    """Detect language for a file path.

    Args:
        path: File path used for extension-based detection
        override: Explicit language name (bypasses extension detection)

    Returns:
        Language name string, or None if undetected
    """
    if override is not None:
        return override
    return EXT_LANGUAGE_MAP.get(path.suffix.lower())


def load_language(name: str) -> object | None:
    """Load and cache a tree-sitter Language for the given language name.

    Most tree-sitter language packages export a top-level ``language()`` factory.
    Some packages with multiple grammars (notably ``tree_sitter_typescript``,
    which ships ``language_typescript()`` and ``language_tsx()``) use a
    package-suffixed name instead. Try the standard form first, then fall back
    to ``language_<name>``.
    """
    if name in _LANGUAGE_CACHE:
        return _LANGUAGE_CACHE[name]

    pkg_name = GRAMMAR_MAP.get(name)
    if pkg_name is None:
        return None

    try:
        mod = importlib.import_module(pkg_name)
        factory = None
        for candidate in ("language", f"language_{name}"):
            if hasattr(mod, candidate):
                factory = getattr(mod, candidate)
                break
        if factory is None:
            return None
        raw = factory()
        if isinstance(raw, tree_sitter.Language):
            lang = raw
        else:
            lang = tree_sitter.Language(raw)
        _LANGUAGE_CACHE[name] = lang
        return lang
    except Exception:
        return None


def parse_file(path: Path, language_name: str) -> tuple[object, bytes] | None:
    """Read ``path`` and parse it with the tree-sitter grammar for ``language_name``.

    Returns ``(tree, content)`` on success, or ``None`` if the grammar
    is unavailable or the parse fails. Handles the Parser API
    compatibility shim between tree-sitter < 0.22 and >= 0.22.

    Used by ``corpus/codebase.py`` for v2 parsing and by
    ``_ast/query.py:_query_file`` for legacy query support.
    """
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


def extract_captures(captures: object) -> dict[str, list]:
    """Normalize tree-sitter captures to a dict mapping capture name → list[Node].

    Handles both dict-style (tree-sitter >= 0.22) and list-style (older) APIs.
    """
    if isinstance(captures, dict):
        return captures
    # list of (node, name) tuples — older API
    if isinstance(captures, list):
        result: dict[str, list] = {}
        for node, name in captures:
            result.setdefault(name, []).append(node)
        return result
    return {}
