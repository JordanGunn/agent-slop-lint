"""The one thing the code-facing layers need from an agreed vocabulary: which word to use.

A vocabulary that a project has agreed (``slop.ontology``) lists, for each concept, the word
to use and the other words that name it: synonyms, abbreviations, retired spellings. A
component that checks names against it needs only this question answered, so it depends on
this protocol and never on the ontology: the dependency points down, to the lexicon.
"""
from __future__ import annotations

from typing import Protocol


class Vocabulary(Protocol):
    def preferred(self, word: str) -> str | None:
        """The word to use instead of ``word`` (case-insensitive), or None when ``word`` is
        already the preferred one or the vocabulary does not name it."""
        ...
