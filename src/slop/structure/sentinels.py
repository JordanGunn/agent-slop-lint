"""Sentinel-parameter detection — flags stringly-typed parameters.

Substrate-aligned port of ``stringly_typed_kernel``. Iterates callables
from the Structure view, asks each grammar to enumerate its parameters
with annotation status, filters by the universal sentinel-name list,
and (where the grammar supports it) enriches with call-site string
literals harvested from the AST.
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING

from slop.structure.records import SentinelParameter

if TYPE_CHECKING:
    from slop.structure.view import Structure


# Universal sentinel-name list — names that signal "this should be an enum".
SENTINEL_NAMES: frozenset[str] = frozenset({
    "status", "mode", "kind", "level", "format",
    "role", "action", "category", "severity", "phase",
    "stage", "style", "direction", "state", "type",
    "method", "strategy", "algorithm", "protocol",
    "encoding", "codec", "backend", "driver", "engine",
})

_STRIP_TRAILING = re.compile(r"_+$")


def compute_sentinels(
    structure: Structure,
    *,
    require_str_annotation: bool = True,
) -> list[SentinelParameter]:
    """Find sentinel-named string-typed parameters across the corpus.

    Call-site literals are always collected; the rule layer applies
    any ``max_cardinality`` filtering.
    """
    from slop.language.grammars import LANGUAGE_BY_ID

    candidates: list[SentinelParameter] = []
    for c in structure.callables():
        path_str = str(c.path)
        node = structure._node_by_key.get((path_str, c.qualname))
        if node is None:
            continue
        language = structure._language_by_path.get(path_str)
        if language is None:
            continue
        lang_cls = LANGUAGE_BY_ID.get(language)
        if lang_cls is None:
            continue
        content = structure._content_by_key.get((path_str, c.qualname), b"")
        for param_name, annotated in lang_cls.stringly_typed_params(node, content):
            sentinel_key = _STRIP_TRAILING.sub("", param_name).lower()
            if sentinel_key not in SENTINEL_NAMES:
                continue
            if require_str_annotation and not annotated and language not in ("ruby",):
                # Python's untyped parameter case: skip when annotation
                # is required. Ruby is dynamic and reports annotated=False
                # by design; allow Ruby sentinels through regardless.
                continue
            short_name = c.qualname.rsplit(".", 1)[-1]
            candidates.append(SentinelParameter(
                file=path_str,
                function_name=short_name,
                param_name=param_name,
                param_line=c.line,
                language=language,
                annotated=annotated,
            ))

    if not candidates:
        return []
    return _enrich_with_call_sites(structure, candidates)


def _enrich_with_call_sites(
    structure: Structure,
    candidates: list[SentinelParameter],
) -> list[SentinelParameter]:
    """Walk every parsed file's call-expressions; collect distinct string
    literals passed to functions named in ``candidates``.

    Substrate-native: uses each grammar's call_node_types + the AST
    structure already in Tree. No external grep needed.
    """
    from slop.language.grammars import LANGUAGE_BY_ID

    wanted: dict[str, list[SentinelParameter]] = {}
    for c in candidates:
        wanted.setdefault(c.function_name, []).append(c)

    literals_by_fn: dict[str, set[str]] = {fn: set() for fn in wanted}

    for parse in structure._parses:
        if parse.root_node is None:
            continue
        lang_cls = LANGUAGE_BY_ID.get(parse.language)
        if lang_cls is None:
            continue
        call_types = lang_cls.call_node_types()
        if not call_types:
            continue

        stack = [parse.root_node]
        while stack:
            n = stack.pop()
            stack.extend(n.children)
            if n.type not in call_types:
                continue
            callee = lang_cls.extract_callee_name(n, parse.content)
            if callee is None or callee not in wanted:
                continue
            args = _arguments_of(n)
            if args is None:
                continue
            for arg in args:
                lit = _string_literal_text(arg, parse.content)
                if lit is not None:
                    literals_by_fn[callee].add(lit)

    out: list[SentinelParameter] = []
    for c in candidates:
        lits = sorted(literals_by_fn.get(c.function_name, ()))
        out.append(SentinelParameter(
            file=c.file,
            function_name=c.function_name,
            param_name=c.param_name,
            param_line=c.param_line,
            language=c.language,
            annotated=c.annotated,
            call_site_literals=tuple(lits),
            call_site_count=len(lits),
        ))
    out.sort(key=lambda e: (e.call_site_count, e.file, e.param_line))
    return out


def _arguments_of(call_node):
    """Return the argument list child for common call shapes, or None."""
    for fname in ("arguments", "argument_list"):
        node = call_node.child_by_field_name(fname)
        if node is not None:
            return [c for c in node.children if c.type not in ("(", ")", ",")]
    return None


def _string_literal_text(arg, content: bytes) -> str | None:
    """Extract the unquoted text of an arg if it is a string literal.

    Handles Python ``string`` (with ``string_content`` child),
    JS/TS ``string`` (with ``string_fragment`` child), Go
    ``interpreted_string_literal``, Ruby ``string`` (with
    ``string_content``), C/C++ ``string_literal`` (with ``string_content``).
    """
    if arg.type in ("string", "string_literal", "interpreted_string_literal"):
        for child in arg.children:
            if child.type in ("string_content", "string_fragment"):
                return content[child.start_byte:child.end_byte].decode(
                    "utf-8", errors="replace",
                )
        # Fall back to the literal text minus surrounding quotes.
        raw = content[arg.start_byte:arg.end_byte].decode("utf-8", errors="replace")
        return raw.strip("\"'`")
    return None
