"""Hammers kernel — configurable banlist of catchall identifier terms.

Catchall words (``Manager``, ``Helper``, ``Util``, ``Spec``, ``Object``,
…) are single-word agent tells. When all you have is a hammer,
everything looks like a nail: the codebase reaches for the same
generic noun every time it needs one, and every responsibility gets
hammered into the same shape regardless of fit.

The harm is two-stage: the original miss, plus the gravitational
sink the catchall becomes for unrelated future responsibilities.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from slop._ast.treesitter import detect_language, load_language
from slop._fs.find import find_kernel
from slop._lexical._naming import enumerate_functions
from slop._lexical._naming import split_identifier
from slop._lexical.verbosity import _CLASS_NODES, _LANG_GLOBS, _extract_type_name


# ---------------------------------------------------------------------------
# Term config
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HammerTerm:
    """One configured banlist entry."""
    word: str
    positions: tuple[str, ...]    # subset of ("prefix", "suffix", "any", "module_name")
    severity: str | None = None   # per-term override; None = use rule default
    exempt_when: tuple[str, ...] = ()


# Default profile — see docs/backlog/02.md for the full rationale.
DEFAULT_PROFILE: tuple[HammerTerm, ...] = (
    HammerTerm("Manager",      ("suffix",), "warning"),
    HammerTerm("Coordinator",  ("suffix",), "warning"),
    HammerTerm("Helper",       ("any", "module_name"), "warning"),
    HammerTerm("Utility",      ("any", "module_name"), "warning"),
    HammerTerm("Util",         ("any", "module_name"), "warning"),
    HammerTerm("Utils",        ("any", "module_name"), "warning"),
    HammerTerm("Handler",      ("suffix",), "info"),
    HammerTerm("Processor",    ("suffix",), "info"),
    HammerTerm("Service",      ("suffix",), "info"),
    HammerTerm("Provider",     ("suffix",), "info"),
    HammerTerm("Engine",       ("suffix",), "info"),
    HammerTerm("Factory",      ("suffix",), "info"),
    HammerTerm("Builder",      ("suffix",), "info"),
    HammerTerm("Wrapper",      ("suffix",), "info"),
    HammerTerm("Adapter",      ("suffix",), "info"),
    HammerTerm("Spec",         ("suffix",), "warning",
               exempt_when=("module_is_test",)),
    HammerTerm("Specification", ("suffix",), "warning",
               exempt_when=("module_is_test",)),
    HammerTerm("Base",         ("suffix",), "warning"),
    HammerTerm("Abstract",     ("prefix",), "info"),
    HammerTerm("Object",       ("suffix",), "error"),
    HammerTerm("Item",         ("suffix",), "error"),
    HammerTerm("Element",      ("suffix",), "error"),
    HammerTerm("Thing",        ("suffix",), "error"),
    HammerTerm("Data",         ("suffix",), "warning"),
    HammerTerm("Info",         ("suffix",), "warning"),
    HammerTerm("Container",    ("suffix",), "warning"),
    HammerTerm("Holder",       ("suffix",), "warning"),
    HammerTerm("Common",       ("module_name", "suffix"), "warning"),
    HammerTerm("Core",         ("module_name", "suffix"), "warning"),
    HammerTerm("Misc",         ("module_name", "suffix"), "warning"),
    HammerTerm("Extra",        ("module_name", "suffix"), "warning"),
    HammerTerm("Shared",       ("module_name", "suffix"), "warning"),
    HammerTerm("Stuff",        ("any",), "error"),
    HammerTerm("Things",       ("any",), "error"),
)


_TEST_PATH_RE = re.compile(r"(^|/)tests?/|test_|_test\.|\.test\.")
_MAIN_PATH_RE = re.compile(r"(^|/)(__main__|main)\.[a-z]+$")


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class WeaselHit:
    name: str
    file: str
    line: int
    language: str
    kind: str            # "function" / "class" / "module"
    matched_word: str
    matched_position: str   # "prefix" / "suffix" / "any" / "module_name"
    severity: str        # final severity (term override or rule default)


@dataclass
class HammersResult:
    items: list[WeaselHit] = field(default_factory=list)
    files_searched: int = 0
    items_analyzed: int = 0
    errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Kernel
# ---------------------------------------------------------------------------


def hammers_kernel(
    root: Path,
    *,
    languages: list[str] | None = None,
    globs: list[str] | None = None,
    excludes: list[str] | None = None,
    hidden: bool = False,
    no_ignore: bool = False,
    terms: tuple[HammerTerm, ...] = DEFAULT_PROFILE,
    default_severity: str = "warning",
) -> HammersResult:
    """Scan function names, class names, and module file names for
    weasel-word matches against the configured banlist."""
    items: list[WeaselHit] = []
    errors: list[str] = []
    files_set: set[str] = set()
    items_analyzed = 0

    by_word: dict[str, HammerTerm] = {t.word.lower(): t for t in terms}

    # 1. Function names
    for ctx in enumerate_functions(
        root,
        languages=languages, globs=globs, excludes=excludes,
        hidden=hidden, no_ignore=no_ignore,
    ):
        items_analyzed += 1
        files_set.add(ctx.file)
        if ctx.name.startswith("<"):
            continue
        hit = _check_identifier(ctx.name, by_word, ctx.file, default_severity)
        if hit is not None:
            word, pos, severity = hit
            items.append(WeaselHit(
                name=ctx.name, file=ctx.file, line=ctx.line,
                language=ctx.language, kind="function",
                matched_word=word, matched_position=pos, severity=severity,
            ))

    # 2. Class names — separate AST walk
    active = (
        {l.lower() for l in languages} & set(_CLASS_NODES)
        if languages else set(_CLASS_NODES)
    )
    find_globs = list(globs) if globs else [
        g for l in sorted(active) for g in _LANG_GLOBS.get(l, [])
    ]
    find_result = find_kernel(
        root=root, globs=find_globs, excludes=excludes,
        hidden=hidden, no_ignore=no_ignore,
    )
    files = [root / e.path for e in find_result.entries if e.type == "file"]

    seen_module_names: set[str] = set()

    for fp in files:
        try:
            rel = str(fp.relative_to(root))
        except ValueError:
            rel = str(fp)
        files_set.add(rel)

        # 3. Module-name check (file stem) — language-agnostic; check
        # once per file.
        stem = fp.stem
        if stem and stem not in seen_module_names:
            seen_module_names.add(stem)
            hit = _check_module_name(stem, by_word, rel, default_severity)
            if hit is not None:
                word, severity = hit
                items.append(WeaselHit(
                    name=stem, file=rel, line=1,
                    language=detect_language(fp) or "<unknown>",
                    kind="module",
                    matched_word=word, matched_position="module_name",
                    severity=severity,
                ))

        lang = detect_language(fp)
        if lang is None or lang not in active or lang not in _CLASS_NODES:
            continue
        class_node_types = _CLASS_NODES[lang]
        tree_lang = load_language(lang)
        if tree_lang is None:
            continue
        try:
            import tree_sitter
            content = fp.read_bytes()
            try:
                parser = tree_sitter.Parser(tree_lang)
                tree = parser.parse(content)
            except TypeError:
                parser = tree_sitter.Parser()
                parser.language = tree_lang  # type: ignore[assignment]
                tree = parser.parse(content)
        except Exception as exc:
            errors.append(f"{fp}: {exc}")
            continue

        stack = [tree.root_node]
        while stack:
            node = stack.pop()
            if node.type in class_node_types:
                items_analyzed += 1
                cname = _extract_type_name(node, content)
                if cname and not cname.startswith("<"):
                    chit = _check_identifier(cname, by_word, rel, default_severity)
                    if chit is not None:
                        word, pos, severity = chit
                        items.append(WeaselHit(
                            name=cname, file=rel,
                            line=node.start_point[0] + 1,
                            language=lang, kind="class",
                            matched_word=word, matched_position=pos,
                            severity=severity,
                        ))
            stack.extend(reversed(node.children))

    return HammersResult(
        items=items,
        files_searched=len(files_set),
        items_analyzed=items_analyzed,
        errors=errors,
    )


# ---------------------------------------------------------------------------
# Matching helpers
# ---------------------------------------------------------------------------


def _check_identifier(
    name: str,
    by_word: dict[str, HammerTerm],
    file_path: str,
    default_severity: str,
) -> tuple[str, str, str] | None:
    """If ``name`` matches any configured term, return
    ``(matched_word, matched_position, severity)``. Else None."""
    tokens = split_identifier(name)
    if not tokens:
        return None
    first_lower = tokens[0].lower()
    last_lower = tokens[-1].lower()

    for token in tokens:
        term = by_word.get(token.lower())
        if term is None:
            continue
        if _is_exempt(term, file_path):
            continue
        # Check requested positions in priority order
        positions = set(term.positions)
        token_lower = token.lower()
        if "prefix" in positions and token_lower == first_lower:
            return (term.word, "prefix", term.severity or default_severity)
        if "suffix" in positions and token_lower == last_lower:
            return (term.word, "suffix", term.severity or default_severity)
        if "any" in positions:
            return (term.word, "any", term.severity or default_severity)
    return None


def _check_module_name(
    stem: str,
    by_word: dict[str, HammerTerm],
    file_path: str,
    default_severity: str,
) -> tuple[str, str] | None:
    """Check the file stem against terms with ``module_name`` position."""
    tokens = split_identifier(stem)
    if not tokens:
        return None
    for token in tokens:
        term = by_word.get(token.lower())
        if term is None:
            continue
        if "module_name" not in term.positions:
            continue
        if _is_exempt(term, file_path):
            continue
        return (term.word, term.severity or default_severity)
    return None


def _is_exempt(term: HammerTerm, file_path: str) -> bool:
    for predicate in term.exempt_when:
        if predicate == "module_is_test" and _TEST_PATH_RE.search(file_path):
            return True
        if predicate == "module_is_main" and _MAIN_PATH_RE.search(file_path):
            return True
    return False
