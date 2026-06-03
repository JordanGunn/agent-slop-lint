"""Packet filters — separate pathological from conventional packets.

A *packet* (from ``Lexicon.packets``) is a set of tokens that travel
together across callables or files. Two genuinely different signals
hide behind the same primitive:

- **Pathological packet** — tokens cluster because no abstraction has
  been extracted. The ``find_kernel`` parameter packet (excludes,
  hidden, ignore, globs, languages) is the textbook case: five
  parameters propagated across 30 files because no ``FindOptions``
  dataclass exists.

- **Conventional packet** — tokens cluster because the architecture
  *requires* every site to use every token. The per-grammar AST node
  category cluster (callable, conditional, loop, operator, …) is
  conventional: the ``Language`` ABC declares every category by
  required method, so each grammar file must use every token. The
  vocabulary is already owned by a defining class.

The distinguishing test: a packet is conventional if its tokens are a
subset of some single class's method-name vocabulary. The class is the
abstraction; the packet just reflects its surface.

See ``docs/research/observations/03-file-scope-packets-and-cross-corpus.md``
for the discovery context and ``observation_04`` for the calibration.
"""
from __future__ import annotations

from typing import Iterable


def split_packets_by_class_ownership(
    packets: Iterable[set[str]],
    class_vocabularies: dict[str, set[str]],
) -> tuple[list[set[str]], list[tuple[set[str], str]]]:
    """Split ``packets`` into ``(pathological, conventional)``.

    A packet is conventional iff there exists some class qualname whose
    vocabulary in ``class_vocabularies`` is a (non-strict) superset of
    the packet. The conventional list carries ``(packet, class_qualname)``
    pairs so callers can cite the owning class.

    A packet may be a subset of multiple classes' vocabularies; the
    first match wins (sorted by qualname for determinism).
    """
    pathological: list[set[str]] = []
    conventional: list[tuple[set[str], str]] = []

    sorted_classes = sorted(class_vocabularies.items())
    for packet in packets:
        owner: str | None = None
        for class_qn, vocab in sorted_classes:
            if packet <= vocab:
                owner = class_qn
                break
        if owner is None:
            pathological.append(set(packet))
        else:
            conventional.append((set(packet), owner))
    return pathological, conventional
