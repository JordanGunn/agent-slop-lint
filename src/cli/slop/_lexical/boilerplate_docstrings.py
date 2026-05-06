"""Boilerplate-docstring kernel — flag docstrings that restate the function name.

A function ``get_user_email`` whose docstring reads "Get the user
email." adds nothing the signature didn't already say. The agent tell
here is the "every function gets a docstring" habit unmoored from
"the docstring should add information."

Detection: tokenize the function name and the docstring's first
sentence. If the docstring's content tokens (after removing
stop-words / function-verb noise) are a subset of the function-name
tokens, flag.

See ``docs/backlog/01.md`` item 4.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from slop._lexical._naming import enumerate_functions
from slop._lexical.identifier_tokens import split_identifier


# Words that don't count as content — articles, prepositions, common
# function verbs, "the/a/an", and connective words. A docstring whose
# only non-stop-word tokens are also in the function name is
# boilerplate.
_STOPWORDS: frozenset[str] = frozenset({
    "a", "an", "the", "this", "that", "these", "those",
    "of", "to", "for", "from", "with", "in", "on", "by", "as", "at",
    "and", "or", "but", "if",
    "is", "are", "was", "were", "be", "been", "being",
    "it", "its", "their", "them",
    # Generic function verbs whose presence in a docstring is purely
    # ornamental when also present in the name.
    "get", "gets", "set", "sets", "return", "returns", "returning",
    "compute", "computes", "calculate", "calculates", "calculated",
    "create", "creates", "creating", "build", "builds", "building",
    "make", "makes", "making", "fetch", "fetches", "load", "loads",
    "save", "saves", "store", "stores", "parse", "parses", "parsed",
    "validate", "validates", "process", "processes", "processed",
    "initialize", "initializes", "initialized", "init",
    "given", "function", "method",
})


@dataclass
class BoilerplateHit:
    function: str
    file: str
    line: int
    language: str
    docstring_first_sentence: str
    function_tokens: list[str]
    docstring_content_tokens: list[str]


@dataclass
class BoilerplateDocstringsResult:
    items: list[BoilerplateHit] = field(default_factory=list)
    files_searched: int = 0
    functions_analyzed: int = 0
    functions_with_docstring: int = 0
    errors: list[str] = field(default_factory=list)


def boilerplate_docstrings_kernel(
    root: Path,
    *,
    languages: list[str] | None = None,
    globs: list[str] | None = None,
    excludes: list[str] | None = None,
    hidden: bool = False,
    no_ignore: bool = False,
    extra_stopwords: frozenset[str] = frozenset(),
) -> BoilerplateDocstringsResult:
    """Walk every Python function definition; extract its docstring (if
    any); flag those whose first sentence's content tokens are a
    subset of the function-name tokens.

    Initial implementation covers Python only — docstring conventions
    in other languages (JSDoc, Javadoc, Doxygen) have radically
    different shapes and are a deliberate follow-up.
    """
    stopwords = _STOPWORDS | extra_stopwords
    items: list[BoilerplateHit] = []
    files_set: set[str] = set()
    fn_count = 0
    with_docstring = 0

    for ctx in enumerate_functions(
        root,
        languages=languages, globs=globs, excludes=excludes,
        hidden=hidden, no_ignore=no_ignore,
    ):
        fn_count += 1
        files_set.add(ctx.file)
        if ctx.language != "python":
            continue
        if ctx.name.startswith("<"):
            continue

        docstring = _extract_python_docstring(ctx)
        if not docstring:
            continue
        with_docstring += 1

        first_sentence = _first_sentence(docstring)
        ds_tokens_raw = _tokenize_docstring(first_sentence)
        ds_content_tokens = [
            t.lower() for t in ds_tokens_raw if t.lower() not in stopwords
        ]
        if not ds_content_tokens:
            # Pure-stopword docstring — also boilerplate, but a
            # different smell. Skip; the rule's specific target is
            # name-restatement.
            continue

        fn_tokens = [t.lower() for t in split_identifier(ctx.name)]
        fn_token_set = set(fn_tokens)
        if all(tok in fn_token_set for tok in ds_content_tokens):
            items.append(BoilerplateHit(
                function=ctx.name, file=ctx.file, line=ctx.line,
                language=ctx.language,
                docstring_first_sentence=first_sentence.strip(),
                function_tokens=fn_tokens,
                docstring_content_tokens=ds_content_tokens,
            ))

    return BoilerplateDocstringsResult(
        items=items,
        files_searched=len(files_set),
        functions_analyzed=fn_count,
        functions_with_docstring=with_docstring,
        errors=[],
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_python_docstring(ctx) -> str | None:
    """Return the function's docstring text if its first body
    statement is a string literal expression. Strips quotes."""
    body = ctx.body_node
    if body is None:
        return None
    # Find first non-trivial statement
    for child in body.children:
        if child.type in (":", "comment"):
            continue
        if child.type == "expression_statement":
            for grand in child.children:
                if grand.type == "string":
                    raw = ctx.content[grand.start_byte:grand.end_byte].decode(
                        "utf-8", errors="replace",
                    )
                    return _strip_quotes(raw)
        return None
    return None


def _strip_quotes(raw: str) -> str:
    """Strip surrounding triple-quote or single-quote markers from a
    Python string literal. Handles ``r``/``b``/``f`` prefixes."""
    s = raw.strip()
    while s and s[0] in "rRbBuUfF":
        s = s[1:]
    for q in ('"""', "'''"):
        if s.startswith(q) and s.endswith(q):
            return s[len(q):-len(q)]
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s[1:-1]
    return s


_SENTENCE_END_RE = re.compile(r"[.!?\n]")


def _first_sentence(docstring: str) -> str:
    s = docstring.strip()
    m = _SENTENCE_END_RE.search(s)
    if m is None:
        return s
    return s[: m.start()]


_WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9]*")


def _tokenize_docstring(text: str) -> list[str]:
    """Split a docstring fragment into word tokens, then split each
    word the same way identifiers are split (snake/Camel)."""
    out: list[str] = []
    for word in _WORD_RE.findall(text):
        out.extend(split_identifier(word))
    return out
