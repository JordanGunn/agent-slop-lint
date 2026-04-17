"""Query kernel - read-only tree-sitter structural search."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from slop._aux.util.treesitter import detect_language, extract_captures, load_language


@dataclass
class AstCapture:
    """A single AST node capture."""

    name: str   # capture name from query (e.g. "func.name")
    text: str   # matched node text
    line: int   # 1-based line number
    col: int    # 0-based column


@dataclass
class AstMatch:
    """All captures from a single query match in a file."""

    file: str
    language: str
    captures: list[AstCapture]


@dataclass
class QueryResult:
    """Aggregated query results."""

    matches: list[AstMatch]
    files_searched: int
    files_with_matches: int
    total_matches: int
    errors: list[str] = field(default_factory=list)


def query_kernel(
    files: list[Path],
    query_str: str,
    *,
    language: str | None = None,
    max_matches: int | None = None,
) -> QueryResult:
    """Execute read-only tree-sitter structural search over a list of files.

    Args:
        files: Files to search
        query_str: Tree-sitter query string
        language: Language override (auto-detected from file extension if None)
        max_matches: Maximum total matches across all files (None = unlimited)

    Returns:
        QueryResult with all matches and aggregate counts.
    """
    all_matches: list[AstMatch] = []
    errors: list[str] = []
    files_with_matches = 0
    total_matches = 0

    for path in files:
        if max_matches is not None and total_matches >= max_matches:
            break

        language_name = detect_language(path, language)
        if language_name is None:
            # Skip — no language detected, not an error
            continue

        lang = load_language(language_name)
        if lang is None:
            errors.append(f"{path}: grammar not installed for language '{language_name}'")
            continue

        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            errors.append(f"{path}: {e}")
            continue

        file_matches = _query_file(path, content, lang, language_name, query_str)

        if file_matches:
            # Apply max_matches cap
            if max_matches is not None:
                remaining = max_matches - total_matches
                file_matches = file_matches[:remaining]

            all_matches.extend(file_matches)
            files_with_matches += 1
            total_matches += len(file_matches)

    return QueryResult(
        matches=all_matches,
        files_searched=len(files),
        files_with_matches=files_with_matches,
        total_matches=total_matches,
        errors=errors,
    )


def _query_file(
    path: Path,
    content: str,
    lang: object,
    language_name: str,
    query_str: str,
) -> list[AstMatch]:
    """Run a tree-sitter query against a single file's content.

    Returns a list of AstMatch, one per match group (pattern firing).
    Supports both modern (0.25.x) and legacy tree-sitter APIs.
    """
    import tree_sitter

    try:
        # Modern API: Parser() no-arg, set language via property
        parser = tree_sitter.Parser()
        parser.language = lang  # type: ignore[assignment]
        content_bytes = content.encode(errors="replace")
        tree = parser.parse(content_bytes)

        # Modern API: Query constructor + QueryCursor
        query_cls = getattr(tree_sitter, "Query", None)
        cursor_cls = getattr(tree_sitter, "QueryCursor", None)
        if query_cls is not None and cursor_cls is not None:
            query = query_cls(lang, query_str)
            return _collect_matches_cursor(
                query, cursor_cls, tree, content_bytes, str(path), language_name,
            )

        # Legacy fallback: lang.query()
        query = lang.query(query_str)  # type: ignore[attr-defined]
        return _collect_matches_legacy(query, tree, content_bytes, str(path), language_name)
    except Exception as e:
        raise RuntimeError(str(e)) from e


def _collect_matches_cursor(
    query: object,
    cursor_cls: type,
    tree: object,
    content_bytes: bytes,
    file_path: str,
    language_name: str,
) -> list[AstMatch]:
    """Collect matches using modern QueryCursor API (tree-sitter >= 0.25)."""
    root_node = tree.root_node  # type: ignore[attr-defined]
    cursor = cursor_cls(query)
    matches: list[AstMatch] = []

    for _pattern_idx, match_dict in cursor.matches(root_node):
        ast_captures = _dict_match_to_captures(match_dict, content_bytes)
        if ast_captures:
            matches.append(AstMatch(
                file=file_path,
                language=language_name,
                captures=ast_captures,
            ))
    return matches


def _collect_matches_legacy(
    query: object,
    tree: object,
    content_bytes: bytes,
    file_path: str,
    language_name: str,
) -> list[AstMatch]:
    """Collect matches using legacy Query API (tree-sitter < 0.25)."""
    root_node = tree.root_node  # type: ignore[attr-defined]
    matches: list[AstMatch] = []

    matches_method = getattr(query, "matches", None)
    if matches_method is not None:
        try:
            raw_matches = matches_method(root_node)
            for _pattern_idx, match_dict in raw_matches:
                ast_captures = _dict_match_to_captures(match_dict, content_bytes)
                if ast_captures:
                    matches.append(AstMatch(
                        file=file_path,
                        language=language_name,
                        captures=ast_captures,
                    ))
            return matches
        except Exception:
            pass

    raw_captures = query.captures(root_node)  # type: ignore[attr-defined]
    cap_dict = extract_captures(raw_captures)
    for cap_name, nodes in cap_dict.items():
        for node in nodes:
            text = content_bytes[node.start_byte:node.end_byte].decode(errors="replace")
            matches.append(AstMatch(
                file=file_path,
                language=language_name,
                captures=[AstCapture(
                    name=cap_name,
                    text=text,
                    line=node.start_point[0] + 1,
                    col=node.start_point[1],
                )],
            ))

    return matches


def _dict_match_to_captures(match_dict: dict, content_bytes: bytes) -> list[AstCapture]:
    """Convert a match dict {capture_name: node_or_list} to AstCapture instances."""
    ast_captures: list[AstCapture] = []
    for cap_name, nodes_or_node in match_dict.items():
        nodes = nodes_or_node if isinstance(nodes_or_node, list) else [nodes_or_node]
        for node in nodes:
            text = content_bytes[node.start_byte:node.end_byte].decode(errors="replace")
            ast_captures.append(AstCapture(
                name=cap_name,
                text=text,
                line=node.start_point[0] + 1,
                col=node.start_point[1],
            ))
    return ast_captures
