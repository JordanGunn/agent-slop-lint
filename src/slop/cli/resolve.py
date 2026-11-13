"""The command line's ``--root``, ``--scope`` and ``--scope-kind``, resolved to what a command reads.

Every function that can fail prints why and returns None, so a command answers with exit 2."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .. import ontology
from ..config import AnalysisConfig
from ..layout import ONTOLOGY_FILENAME, STATE_DIR
from ..identity import relative_path
from ..rules import RULE_REGISTRY
from ..scope import scan_corpus
from ..scope.find import walk
from ..scope.identity import ScopeKind


def add_root(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--root", default=".", help="source root to scan (default: cwd)")


def add_scope(parser: argparse.ArgumentParser, help: str, *, kind: bool = True) -> None:
    """``--scope`` and, with ``kind``, the ``--scope-kind`` that picks one of several matches."""
    parser.add_argument("--scope", default=None, help=help)
    if kind:
        parser.add_argument("--scope-kind", default=None,
                            help="pick one kind when --scope names several (a package and its __init__ module)")


def has_source(corpus) -> bool:
    """True if the scanned corpus contains at least one module. A nonexistent or
    source-free root yields an empty corpus; linting it would visit zero scopes and
    report "clean", a false pass, so the CLI treats it as an error."""
    return any(scope.id.kind is ScopeKind.MODULE for scope in walk(corpus))


def scan(root: str | Path):
    """Carve ``root`` into a corpus for a view, or None.

    Views answer questions and never judge, so they read only the config's scan settings
    (``exclude``), not its ``[rules]``: a ``.slop.toml`` naming a rule slop no longer has is a
    ``lint`` error, not a reason to refuse to print a name's definitions."""
    root = Path(root)
    if not root.exists():
        print(f"slop: error: root path does not exist: {root}", file=sys.stderr)
        return None
    corpus = scan_corpus(root, AnalysisConfig.load(root, RULE_REGISTRY))
    if not has_source(corpus):
        print(f"slop: error: no source files found under {root}", file=sys.stderr)
        return None
    return corpus


def project_root(root: Path, config: AnalysisConfig) -> Path:
    """The directory holding the config, else the scan root (its directory, for a file)."""
    return config.anchor or (root if root.is_dir() else root.parent)


def parse_kind(kind: str | None) -> ScopeKind | None:
    if kind is None:
        return None
    try:
        return ScopeKind(kind)
    except ValueError:
        raise ValueError(
            f"unknown kind '{kind}' (choose from {', '.join(k.value for k in ScopeKind)})"
        ) from None


def matches(corpus, ident: str, kind: ScopeKind | None = None) -> list:
    """Scopes matching ``ident`` by qualname or by relative file path, optionally of one
    ``kind``. A list, since a bare qualname can repeat (``view`` in two packages,
    overloads) and a package shares its qualname with its ``__init__`` module."""
    root = str(corpus.root)
    # qualname matches any kind; a path identifies a file, so it matches the MODULE only
    # (every callable/class in the file shares that path, but the file *is* the module).
    return [c for c in walk(corpus)
            if (c.qualname == ident
                or (c.id.kind is ScopeKind.MODULE and relative_path(c.id, root) == ident))
            and (kind is None or c.id.kind is kind)]


def select(corpus, ident: str, kind: ScopeKind | None = None):
    """The one scope ``ident`` names, or None: nothing matched, or it was ambiguous (each
    candidate and its kind is listed; ``--scope-kind`` or a path picks one)."""
    found = matches(corpus, ident, kind)
    if not found:
        print(f"slop: error: no scope with qualname or path '{ident}'", file=sys.stderr)
        return None
    if len(found) > 1:
        print(f"slop: error: '{ident}' is ambiguous ({len(found)} matches); "
              "disambiguate with --scope-kind or by path:", file=sys.stderr)
        for m in found:
            print(f"  {m.id.kind.value:<8} {relative_path(m.id, str(corpus.root)) or m.qualname}",
                  file=sys.stderr)
        return None
    return found[0]


def target(corpus, scope: str | None, scope_kind: str | None):
    """The scope a view reports on: ``scope`` if given, else the whole corpus. None if
    ``scope`` names no single scope."""
    return corpus if scope is None else select(corpus, scope, parse_kind(scope_kind))


def ontology_path(root: str | Path) -> Path:
    """Where the project's vocabulary lives: ``.slop/ontology.json`` under the project root."""
    root = Path(root)
    return project_root(root, AnalysisConfig.load(root, RULE_REGISTRY)) / STATE_DIR / ONTOLOGY_FILENAME


def vocabulary(root: str | Path) -> ontology.Scheme | None:
    """The project's vocabulary, or None when it has none yet. Raises ``OntologyError`` when the
    file exists but cannot be read."""
    file = ontology_path(root)
    return ontology.load(file) if file.exists() else None


def relative(path: str, corpus) -> str:
    """``path`` relative to the corpus root, for display."""
    try:
        return os.path.relpath(path, corpus.root)
    except ValueError:
        return path
