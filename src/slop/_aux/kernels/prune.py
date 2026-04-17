"""Prune kernel - tiered dead code candidate audit."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from slop._aux.kernels.find import find_kernel
from slop._aux.kernels.grep import grep_kernel


ADVISORY = (
    "STATIC ANALYSIS ONLY: These candidates have zero detected references. "
    "grep cannot see dynamic dispatch, reflection, plugin registration, or cross-language calls. "
    "Each candidate requires human verification before any action. "
    "Confidence ratings reflect name-length and language risk, not certainty."
)

COMMON_NAMES = {
    "run", "main", "setup", "init", "start", "stop", "get", "set",
    "update", "create", "delete", "load", "save", "process",
    "execute", "handle", "build", "parse", "check", "validate",
}

DYNAMIC_LANGUAGES = {"python", "javascript", "ruby"}


@dataclass
class PruneCandidate:
    """A dead-code candidate with confidence metadata."""

    symbol: str
    symbol_type: str        # "function"|"class"|"file"|"interface" etc.
    file: str               # absolute path of definition/module file
    line: int               # definition line (0 for file-scope candidates)
    external_refs: int      # references outside the definition file
    confidence: str         # "high"|"medium"|"low"
    caveats: list[str]


@dataclass
class PruneResult:
    """Aggregated prune results."""

    candidates: list[PruneCandidate]
    symbols_analyzed: int
    files_searched: int
    scope: list[str]
    errors: list[str] = field(default_factory=list)
    truncated: bool = False


def prune_kernel(
    root: Path,
    *,
    globs: list[str] | None = None,
    excludes: list[str] | None = None,
    scope: list[Literal["files", "symbols"]] | None = None,
    language: str | None = None,
    min_name_length: int = 4,
    max_refs: int = 0,
    hidden: bool = False,
    no_ignore: bool = False,
    max_symbols: int | None = None,
) -> PruneResult:
    """Audit a codebase for dead code candidates.

    Args:
        root: Search root directory
        globs: Include glob patterns
        excludes: Exclude glob patterns
        scope: Analysis scopes ("files" and/or "symbols"); default ["symbols"]
        language: Tree-sitter language override for symbols scope
        min_name_length: Skip symbols shorter than this
        max_refs: Flag candidates with <= N external refs (0 = zero-ref only)
        hidden: Search hidden files
        no_ignore: Don't respect gitignore
        max_symbols: Cap on symbols analyzed (performance safety valve)

    Returns:
        PruneResult with candidates, summary, and error list
    """
    if scope is None:
        scope = ["symbols"]

    # File discovery
    find_result = find_kernel(
        root=root,
        globs=globs,
        excludes=excludes,
        hidden=hidden,
        no_ignore=no_ignore,
    )

    file_paths = [root / e.path for e in find_result.entries if e.type == "file"]
    errors: list[str] = list(find_result.errors)

    candidates: list[PruneCandidate] = []
    symbols_analyzed = 0

    if "files" in scope:
        file_candidates, file_analyzed, file_errors = _analyze_files(
            file_paths=file_paths,
            root=root,
            min_name_length=min_name_length,
            max_refs=max_refs,
        )
        candidates.extend(file_candidates)
        symbols_analyzed += file_analyzed
        errors.extend(file_errors)

    if "symbols" in scope:
        sym_candidates, sym_analyzed, sym_errors, truncated = _analyze_symbols(
            file_paths=file_paths,
            root=root,
            language=language,
            min_name_length=min_name_length,
            max_refs=max_refs,
            max_symbols=max_symbols,
        )
        candidates.extend(sym_candidates)
        symbols_analyzed += sym_analyzed
        errors.extend(sym_errors)
    else:
        truncated = False

    return PruneResult(
        candidates=candidates,
        symbols_analyzed=symbols_analyzed,
        files_searched=find_result.total_found,
        scope=scope,
        errors=errors,
        truncated=truncated,
    )


def _analyze_files(
    file_paths: list[Path],
    root: Path,
    min_name_length: int,
    max_refs: int,
) -> tuple[list[PruneCandidate], int, list[str]]:
    """File-scope analysis: find module files with no external references to their stem."""
    candidates: list[PruneCandidate] = []
    errors: list[str] = []
    analyzed = 0

    for file_path in file_paths:
        stem = file_path.stem
        if len(stem) < min_name_length:
            continue

        analyzed += 1
        # Search other files for the stem as a whole word
        other_files = [f for f in file_paths if f != file_path]
        if not other_files:
            external_refs = 0
        else:
            grep_result = grep_kernel(
                patterns=[{"kind": "fixed", "value": stem}],
                root=root,
                files=other_files,
                mode="fixed",
                case="sensitive",
            )
            errors.extend(grep_result.errors)
            # Count only word-boundary matches — use rg --word-regexp approximation
            # by filtering: stem must appear as a standalone token
            external_refs = sum(
                1 for m in grep_result.matches
                if _is_word_match(m.content, stem)
            )

        if external_refs <= max_refs:
            confidence, caveats = _compute_confidence(stem, "module", None)
            candidates.append(PruneCandidate(
                symbol=stem,
                symbol_type="module",
                file=str(file_path),
                line=0,
                external_refs=external_refs,
                confidence=confidence,
                caveats=caveats,
            ))

    return candidates, analyzed, errors


def _is_word_match(content: str, word: str) -> bool:
    """Check if word appears as a standalone identifier in content."""
    import re
    return bool(re.search(r"\b" + re.escape(word) + r"\b", content))


def _analyze_symbols(
    file_paths: list[Path],
    root: Path,
    language: str | None,
    min_name_length: int,
    max_refs: int,
    max_symbols: int | None,
) -> tuple[list[PruneCandidate], int, list[str], bool]:
    """Symbol-scope analysis: find top-level definitions with no external references."""
    from slop._aux.kernels.query import query_kernel
    from slop._aux.kernels.usages import DEFINITION_QUERIES
    from slop._aux.util.treesitter import detect_language

    candidates: list[PruneCandidate] = []
    errors: list[str] = []

    # Group files by language
    if language:
        lang_files: dict[str, list[Path]] = {}
        if language in DEFINITION_QUERIES:
            lang_files[language] = file_paths
        else:
            return [], 0, [f"No definition queries for language '{language}'"], False
    else:
        lang_files = {}
        for f in file_paths:
            lang = detect_language(f)
            if lang and lang in DEFINITION_QUERIES:
                lang_files.setdefault(lang, []).append(f)

    # Enumerate definitions: (symbol, symbol_type, file_path, line)
    definitions: list[tuple[str, str, str, int]] = []
    seen: set[tuple[str, str]] = set()  # (symbol, abs_file) dedup

    for lang_name, lang_file_list in lang_files.items():
        for query_str, sym_type in DEFINITION_QUERIES[lang_name]:
            result = query_kernel(
                files=lang_file_list,
                query_str=query_str,
                language=lang_name,
            )
            errors.extend(result.errors)
            for match in result.matches:
                for cap in match.captures:
                    if cap.name == "name":
                        key = (cap.text, match.file)
                        if key not in seen:
                            seen.add(key)
                            definitions.append((cap.text, sym_type, match.file, cap.line))

    # Filter by min_name_length
    definitions = [
        (sym, stype, fpath, line)
        for sym, stype, fpath, line in definitions
        if len(sym) >= min_name_length
    ]

    # Apply max_symbols cap
    truncated = False
    if max_symbols is not None and len(definitions) > max_symbols:
        definitions = definitions[:max_symbols]
        truncated = True

    analyzed = len(definitions)

    # For each definition, count external references
    for sym, sym_type, def_file, line in definitions:
        other_files = [f for f in file_paths if str(f) != def_file]

        if not other_files:
            external_refs = 0
        else:
            grep_result = grep_kernel(
                patterns=[{"kind": "fixed", "value": sym}],
                root=root,
                files=other_files,
                mode="fixed",
                case="sensitive",
            )
            errors.extend(grep_result.errors)
            external_refs = grep_result.total_matches

        if external_refs <= max_refs:
            # Detect language for confidence heuristic
            lang_name = _lang_for_file(def_file, lang_files)
            confidence, caveats = _compute_confidence(sym, sym_type, lang_name)
            candidates.append(PruneCandidate(
                symbol=sym,
                symbol_type=sym_type,
                file=def_file,
                line=line,
                external_refs=external_refs,
                confidence=confidence,
                caveats=caveats,
            ))

    return candidates, analyzed, errors, truncated


def _lang_for_file(file_str: str, lang_files: dict[str, list[Path]]) -> str | None:
    """Look up the language for a file path from the grouped lang_files map."""
    for lang, paths in lang_files.items():
        if any(str(p) == file_str for p in paths):
            return lang
    return None


def _compute_confidence(
    symbol: str,
    symbol_type: str,
    language: str | None,
) -> tuple[str, list[str]]:
    """Compute confidence rating and caveats for a candidate symbol."""
    caveats: list[str] = []
    score = 3

    # Dunder methods — always low
    if symbol.startswith("__") and symbol.endswith("__"):
        return "low", ["dunder method — may be invoked by runtime, not visible in source"]

    # Name length
    if len(symbol) <= 4:
        caveats.append(f"short name ({len(symbol)} chars) — high false-positive risk")
        score -= 2
    elif len(symbol) <= 7:
        caveats.append(
            f"short-medium name ({len(symbol)} chars) — may match unrelated symbols"
        )
        score -= 1

    # Common names
    if symbol.lower() in COMMON_NAMES:
        caveats.append(f"common name '{symbol}' — likely to match unrelated identifiers")
        score -= 2

    # Dynamic language risk
    if language in DYNAMIC_LANGUAGES:
        caveats.append(
            f"{language}: reflection and dynamic dispatch cannot be detected statically"
        )
        score -= 1

    confidence = "high" if score >= 3 else ("medium" if score >= 1 else "low")
    return confidence, caveats


def build_next_steps(candidates: list[PruneCandidate], root: Path, globs: list[str]) -> dict:
    """Build the next_steps field for PruneResult output."""
    if not candidates:
        return {
            "message": (
                "No candidates found within the current scope and thresholds. "
                "The codebase appears fully referenced — or widen scope with max_refs, "
                "different globs, or both scopes."
            ),
            "verify_command": f"aux usages <symbol> --root {root}",
        }

    by_conf = Counter(c.confidence for c in candidates)
    parts = [f"{v} {k}" for k, v in sorted(by_conf.items())]
    conf_str = ", ".join(parts)
    n = len(candidates)
    glob_hint = f" --glob \"{globs[0]}\"" if globs else ""
    message = (
        f"Found {n} candidate{'s' if n != 1 else ''} ({conf_str}). "
        f"This is a first-pass static scan. Before taking any action, "
        f"I can trace the full reference chain for each using `aux usages` — this will "
        f"surface dynamic call paths and narrow the list further. "
        f"Would you like me to investigate any of these in more detail?"
    )
    return {
        "message": message,
        "verify_command": f"aux usages <symbol> --root {root}{glob_hint}",
    }
