"""Draft a vocabulary from code: the words a codebase already uses, as a starting point to agree on.

One entity per public class: its name, its properties as fields (where the grammar can read
them: Python, JavaScript, TypeScript), and the first sentence of its docstring as the
description (Python). A class whose name does not fit an Open Ontology entity name (a private
``_Base``) is left out: it is an implementation detail, not vocabulary. When classes in
different files share a name, the first by path is drafted; the overload is a finding, not a
choice the draft makes. The draft is complete and noisy by design: deciding which words matter
and what they mean is judgement, made afterwards.
"""
from __future__ import annotations

import re
from typing import Any

from ..lexicon.tokenize import split_tokens
from ..scope.identity import ScopeKind
from .interface import Term, TermKind, normalize
from .ir import OntologyIR

ENTITY_NAME = re.compile(r"^[A-Z][A-Za-z0-9]*$")
_FIELD_NAME = re.compile(r"^[a-z][a-z0-9_-]*$")


def draft(corpus: Any, *, name: str) -> OntologyIR:
    """The draft vocabulary of ``corpus``, labelled ``name``."""
    classes = sorted(_classes(corpus), key=lambda c: (str(c.files[0]) if c.files else "", c.line))
    terms: list[Term] = []
    seen: set[str] = set()
    for cls in classes:
        if not ENTITY_NAME.match(cls.name) or normalize(cls.name) in seen:
            continue
        seen.add(normalize(cls.name))
        namespace = "-".join(token.lower() for token in split_tokens(cls.name))
        fields = tuple(dict.fromkeys(f"{namespace}/{f}" for f in map(_field_name, cls.properties()) if f))
        terms.append(Term(cls.name, TermKind.ENTITY, _first_sentence(cls), fields))
    return OntologyIR(f"{name}@0.1.0", terms)


def _classes(corpus: Any):
    stack = [corpus]
    while stack:
        component = stack.pop()
        if component.id.kind is ScopeKind.CLASS:
            yield component
        stack.extend(component.children())


def _field_name(prop: str) -> str | None:
    """A property as an Open Ontology field name: no leading underscores, lower case."""
    name = prop.lstrip("_").lower()
    return name if _FIELD_NAME.match(name) else None


def _first_sentence(cls: Any) -> str | None:
    text = cls._grammar.docstring(cls._node, cls._content)
    if not text:
        return None
    paragraph = " ".join(text.strip().split("\n\n", 1)[0].split())
    match = re.match(r"(.+?[.!?])(\s|$)", paragraph)
    return match.group(1) if match else paragraph
