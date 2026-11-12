"""Two spellings are one word when they differ only by case or inflection."""
from __future__ import annotations

import pytest

from slop.lexicon import Lexicon, Role, plural, stem
from slop.span import Span


@pytest.mark.parametrize("a, b", [
    ("Node", "nodes"), ("class", "Classes"), ("entry", "entries"), ("key", "keys"),
    ("property", "PROPERTIES"), ("use", "uses"), ("address", "addresses"),
])
def test_inflections_share_a_stem(a: str, b: str):
    assert stem(a) == stem(b)


@pytest.mark.parametrize("a, b", [("process", "processor"), ("class", "clas"), ("new", "node"), ("status", "state")])
def test_different_words_keep_different_stems(a: str, b: str):
    assert stem(a) != stem(b)


@pytest.mark.parametrize("word, expected", [
    ("node", "nodes"), ("entry", "entries"), ("key", "keys"), ("class", "classes"),
    ("box", "boxes"), ("match", "matches"), ("Term", "Terms"),
])
def test_plural_is_the_regular_english_plural(word: str, expected: str):
    assert plural(word) == expected


def test_a_lexicon_counts_inflections_as_one_word_and_tests_stop_words_on_the_spelling():
    units = [(name, Role.CALLABLE, Span("a.py", 0, 1)) for name in ("node", "node_count", "nodes", "NodeSet", "is")]
    lexicon = Lexicon(units)
    assert lexicon.frequencies() == {stem("node"): 4, stem("count"): 1, stem("set"): 1}       # "is" is a stop word, tested before stemming would make it "i"
    assert lexicon.spellings()[stem("nodes")] == "node"
