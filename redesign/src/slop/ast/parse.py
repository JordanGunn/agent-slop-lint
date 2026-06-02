"""Parse substrate — tree-sitter grammar loading + file parsing.

Infrastructure ported faithfully from the legacy ``tree/parse.py`` +
``language/treesitter.py``: tree-sitter's loader and parser API are a real
external constraint, not a structural choice, so this is a direct port (the
pre/post-0.22 Parser shim stays). Detection maps a path to a language id by
extension; loading resolves + caches a ``tree_sitter.Language``.
"""
from __future__ import annotations

import importlib
from pathlib import Path

import tree_sitter

# language id -> tree-sitter package
_GRAMMAR_PACKAGES: dict[str, str] = {
    "python": "tree_sitter_python",
    "javascript": "tree_sitter_javascript",
    "typescript": "tree_sitter_typescript",
    "rust": "tree_sitter_rust",
    "go": "tree_sitter_go",
    "java": "tree_sitter_java",
    "c": "tree_sitter_c",
    "cpp": "tree_sitter_cpp",
    "ruby": "tree_sitter_ruby",
    "c_sharp": "tree_sitter_c_sharp",
    "julia": "tree_sitter_julia",
}

# extension -> language id
EXTENSION_LANGUAGE: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript", ".tsx": "typescript",
    ".rs": "rust",
    ".go": "go",
    ".java": "java",
    ".c": "c", ".h": "c",
    ".cpp": "cpp", ".cc": "cpp", ".cxx": "cpp", ".hpp": "cpp", ".hxx": "cpp",
    ".rb": "ruby",
    ".cs": "c_sharp",
    ".jl": "julia",
}

_LANGUAGE_CACHE: dict[str, object] = {}


def detect_language(path: Path) -> str | None:
    """Language id for a file path by extension, or None if unrecognised."""
    return EXTENSION_LANGUAGE.get(path.suffix.lower())


def load_ts_language(language_id: str) -> object | None:
    """Load + cache a ``tree_sitter.Language`` for a language id, or None."""
    if language_id in _LANGUAGE_CACHE:
        return _LANGUAGE_CACHE[language_id]
    pkg = _GRAMMAR_PACKAGES.get(language_id)
    if pkg is None:
        return None
    try:
        mod = importlib.import_module(pkg)
        factory = None
        for candidate in ("language", f"language_{language_id}"):
            if hasattr(mod, candidate):
                factory = getattr(mod, candidate)
                break
        if factory is None:
            return None
        raw = factory()
        lang = raw if isinstance(raw, tree_sitter.Language) else tree_sitter.Language(raw)
        _LANGUAGE_CACHE[language_id] = lang
        return lang
    except Exception:
        return None


def parse_bytes(content: bytes, language_id: str) -> object | None:
    """Parse source bytes with the grammar for ``language_id``; tree or None."""
    ts_lang = load_ts_language(language_id)
    if ts_lang is None:
        return None
    try:
        try:
            parser = tree_sitter.Parser(ts_lang)
        except TypeError:  # pre-0.22 API
            parser = tree_sitter.Parser()
            parser.language = ts_lang  # type: ignore[assignment]
        return parser.parse(content)
    except Exception:
        return None


def parse_file(path: Path, language_id: str) -> tuple[object, bytes] | None:
    """Read + parse ``path``; ``(tree, content)`` or None on read/parse failure."""
    try:
        content = path.read_bytes()
    except OSError:
        return None
    tree = parse_bytes(content, language_id)
    if tree is None:
        return None
    return tree, content
