"""Inflection: when two spellings are one word, and how to inflect a word to match another.

``stem`` is the key under which slop counts and compares words: the word lower-cased, its
plural or third-person ``-s`` removed, and a final ``y`` after a vowel-bearing stem turned to
``i``, so ``Node``, ``nodes``, ``entry`` and ``entries`` meet as ``node`` and ``entri``. These
are steps 1a and 1c of Porter's stemmer (Porter 1980, "An algorithm for suffix stripping"),
which only undo inflection; the later steps strip derivational suffixes (``-ation``,
``-ness``) and would merge different words. A stem is a key, not a word: show the spelling the
code uses instead (``Lexicon.spellings``).

Known limits, by design of step 1a: irregular plurals (``indices``, ``children``) and ``-es``
after a single ``s`` (``aliases``) keep their own stem. On slop's and laszy's own words
(2026-11-12) it merged 127 groups, every one a singular and plural or a verb and its ``-s``
form, and no two different words.
"""
from __future__ import annotations

_VOWELS = frozenset("aeiou")


def stem(word: str) -> str:
    """The key ``word`` is counted and compared under: lower case, inflection removed."""
    word = word.lower()
    if word.endswith("sses") or word.endswith("ies"):
        word = word[:-2]
    elif word.endswith("s") and not word.endswith("ss"):
        word = word[:-1]
    if word.endswith("y") and any(c in _VOWELS for c in word[:-1]):
        word = word[:-1] + "i"
    return word


def plural(word: str) -> str:
    """The regular English plural of ``word``: ``entry`` -> ``entries``, ``class`` ->
    ``classes``, ``node`` -> ``nodes``."""
    lower = word.lower()
    if lower.endswith("y") and len(lower) > 1 and lower[-2] not in _VOWELS:
        return word[:-1] + "ies"
    if lower.endswith(("s", "x", "z", "ch", "sh")):
        return word + "es"
    return word + "s"
