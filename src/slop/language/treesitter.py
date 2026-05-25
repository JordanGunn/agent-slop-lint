"""Grammar loading + file→language detection.

Internal to the language substrate. ``load_language`` resolves a
language name to a cached ``tree_sitter.Language``; ``detect_language``
maps a file path to its language id via extension lookup.

``GRAMMAR_MAP`` lists every language slop ships a grammar for;
``EXT_LANGUAGE_MAP`` is the source-of-truth path→language mapping.
Both are consumed by ``Tree.scan()`` during corpus discovery.
"""
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

_LANGUAGE_CACHE: dict[str, object] = {}


def detect_language(path: Path, override: str | None = None) -> str | None:
    """Detect language for a file path.

    ``override`` short-circuits extension detection (e.g., when the
    caller already knows the language id).
    """
    if override is not None:
        return override
    return EXT_LANGUAGE_MAP.get(path.suffix.lower())


def load_language(name: str) -> object | None:
    """Load and cache a tree-sitter Language by language name.

    Most tree-sitter packages export a top-level ``language()`` factory;
    a few with multiple grammars (notably ``tree_sitter_typescript``,
    which ships ``language_typescript()`` / ``language_tsx()``) use a
    package-suffixed name. Tries the standard form first, then falls
    back to ``language_<name>``.
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
