"""Pairwise comparison primitives — the relational lexicostatistics layer.

These are pure functions over token-frequency maps; the tests pin their range,
symmetry, and the directional vs symmetric contract so the measurement probe (and any
future cohesion/relocation rule) can trust them.
"""
from __future__ import annotations

import math

from slop.lexicon import comparison as cmp


def test_jaccard_bounds_and_overlap():
    assert cmp.jaccard({}, {}) == 0.0
    assert cmp.jaccard({"a": 1, "b": 1}, {"a": 9, "b": 9}) == 1.0          # same set, freq ignored
    assert cmp.jaccard({"a": 1}, {"b": 1}) == 0.0                          # disjoint
    # {a,b,c} vs {b,c,d}: intersection 2, union 4
    assert cmp.jaccard({"a": 1, "b": 1, "c": 1}, {"b": 1, "c": 1, "d": 1}) == 0.5


def test_containment_is_directional():
    a = {"x": 1, "y": 1}              # small, fully inside b
    b = {"x": 1, "y": 1, "z": 1, "w": 1}
    assert cmp.containment(a, b) == 1.0      # all of a is in b
    assert cmp.containment(b, a) == 0.5      # half of b is in a
    assert cmp.containment({}, b) == 0.0


def test_cosine_tracks_proportion_not_presence():
    a = {"a": 3, "b": 1}
    assert math.isclose(cmp.cosine(a, a), 1.0)                # identical
    assert cmp.cosine({"a": 1}, {"b": 1}) == 0.0             # orthogonal
    # same tokens, inverted balance -> high but not perfect
    c = cmp.cosine({"a": 3, "b": 1}, {"a": 1, "b": 3})
    assert 0.0 < c < 1.0


def test_js_divergence_bounds_and_symmetry():
    a = {"a": 2, "b": 1}
    b = {"b": 1, "c": 2}
    assert cmp.js_divergence(a, a) == 0.0                     # identical distributions
    assert math.isclose(cmp.js_divergence({"a": 1}, {"b": 1}), 1.0)   # disjoint -> max
    assert math.isclose(cmp.js_divergence(a, b), cmp.js_divergence(b, a))  # symmetric
    assert 0.0 <= cmp.js_divergence(a, b) <= 1.0
    assert cmp.js_divergence({}, a) == 1.0                    # empty side is maximally divergent


def test_js_similarity_is_complement():
    a = {"a": 2, "b": 1}
    b = {"b": 1, "c": 2}
    assert math.isclose(cmp.js_similarity(a, b), 1.0 - cmp.js_divergence(a, b))
    assert cmp.js_similarity(a, a) == 1.0
