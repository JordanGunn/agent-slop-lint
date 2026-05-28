"""Identifier tokenisation — split camelCase / snake_case names into tokens.

Extracted from ``Lexicon.split_tokens`` so that substrate-internal modules
(``affix``, ``_profile``) can tokenise without importing the full view.
"""
from __future__ import annotations

import re

_CAMEL_LOWER_UPPER = re.compile(r"([a-z])([A-Z])")
_CAMEL_UPPER_TITLE = re.compile(r"([A-Z]+)([A-Z][a-z])")


def split_tokens(name: str) -> tuple[str, ...]:
    """Split an identifier into word tokens (snake_case + CamelCase aware).

    ``my_func`` → ``("my", "func")``; ``processData`` → ``("process", "Data")``;
    ``HTTPClient`` → ``("HTTP", "Client")``; ``__init__`` → ``("init",)``.
    """
    cleaned = name.strip("_")
    cleaned = _CAMEL_LOWER_UPPER.sub(r"\1_\2", cleaned)
    cleaned = _CAMEL_UPPER_TITLE.sub(r"\1_\2", cleaned)
    return tuple(p for p in re.split(r"[_\d]+", cleaned) if p)
