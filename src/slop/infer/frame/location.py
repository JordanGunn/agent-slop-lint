"""Where a residue's code is: the lines a scope owns.

A scope's extent (``slop.identity.Extent``) is the authoritative record of the source it owns,
as byte spans: a class or callable its definition, a module its file, a package every module
file in it. A residue shows the whole lines those spans touch, and its fingerprint covers the
same lines, so what the judge reads is what a ruling is checked against.
"""
from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from ...identity import project_path
from ...span import Span
from ..contract import Location


def locations(spans: Iterable[Span], root: Path) -> tuple[Location, ...]:
    """The whole lines each span touches, once each, in the spans' order; paths relative to
    ``root``."""
    return tuple(Location(path=project_path(path, root), first_line=first, last_line=last)
                 for path, first, last in _lines(spans))


def code(spans: Iterable[Span]) -> str:
    """The text of the whole lines the spans touch, joined in the spans' order."""
    return "\n".join(_read(path, first, last) for path, first, last in _lines(spans))


def _lines(spans: Iterable[Span]) -> list[tuple[str, int, int]]:
    """``(path, first line, last line)`` of each span, 1-based and inclusive, without repeats."""
    places: dict[tuple[str, int, int], None] = {}
    for span in spans:
        content = Path(span.path).read_bytes()
        first = content.count(b"\n", 0, span.start_byte) + 1
        last = content.count(b"\n", 0, max(span.end_byte - 1, span.start_byte)) + 1
        places.setdefault((span.path, first, last), None)
    return list(places)


def _read(path: str, first: int, last: int) -> str:
    return "\n".join(Path(path).read_text(encoding="utf-8", errors="replace").splitlines()[first - 1:last])
