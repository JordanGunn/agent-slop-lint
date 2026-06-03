"""Identifier tokeniser.

Copied from src/cli/slop/_lexical/_naming.py for scaffolding
isolation. The live tree is the source of truth; when this
scaffolding is promoted, the import is rewired and this copy is
deleted.
"""
from __future__ import annotations

import re

_CAMEL_LOWER_UPPER = re.compile(r"([a-z])([A-Z])")
_CAMEL_UPPER_TITLE = re.compile(r"([A-Z]+)([A-Z][a-z])")


def split_identifier(name: str) -> list[str]:
    """Split a snake_case or CamelCase identifier into word tokens.

    Examples::

        split_identifier("my_func")       -> ["my", "func"]
        split_identifier("processData")   -> ["process", "Data"]
        split_identifier("HTTPClient")    -> ["HTTP", "Client"]
        split_identifier("__init__")      -> ["init"]
        split_identifier("x")             -> ["x"]
    """
    name = name.strip("_")
    name = _CAMEL_LOWER_UPPER.sub(r"\1_\2", name)
    name = _CAMEL_UPPER_TITLE.sub(r"\1_\2", name)
    return [p for p in re.split(r"[_\d]+", name) if p]
