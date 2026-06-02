"""Granular scoping — a view over a *union* of scopes composes.

The headline capability: ``Structure``/``Lexicon`` over a ``Selection`` of scopes sees
the union. Additive structural metrics sum; the lexicon is the combined vocabulary.
Altitude-bound metrics (CK/Martin) stay altitude-bound and are not offered over an
arbitrary union.
"""
from pathlib import Path

from slop.scope import scan_corpus, Selection
from slop.scope.identity import ComponentKind
from slop.scope.lexicon import build_lexicon
from slop.metrics.structural.view import Structure

SRC = '''\
class Alpha:
    def parse_alpha(self, raw_token):
        if raw_token:
            return transform_token(raw_token)
        return None

class Beta:
    def render_beta(self, widget_node):
        for child in widget_node:
            paint(child)
        return widget_node
'''


def _classes(tmp_path: Path):
    (tmp_path / "m.py").write_text(SRC)
    mod = scan_corpus(tmp_path, config=None).realms()[0].packages()[0].modules()[0]
    classes = {c.name: c for c in mod.children() if c.KIND == ComponentKind.CLASS}
    return classes["Alpha"], classes["Beta"]


def test_additive_metric_sums_over_the_union(tmp_path: Path):
    alpha, beta = _classes(tmp_path)
    sel = Selection([alpha, beta])
    a, b = Structure.over(alpha).cyclomatic(), Structure.over(beta).cyclomatic()
    union = Structure.over(sel).cyclomatic()
    assert a > 0 and b > 0
    assert union == a + b                 # composes additively
    assert union > a and union > b        # a real union, not a degenerate single scope


def test_lexicon_over_the_union_is_the_combined_vocabulary(tmp_path: Path):
    alpha, beta = _classes(tmp_path)
    sel = Selection([alpha, beta])
    toks_a = set(build_lexicon(alpha).tokens())
    toks_b = set(build_lexicon(beta).tokens())
    toks_union = set(build_lexicon(sel).tokens())
    assert toks_union == toks_a | toks_b
    # each scope contributes vocabulary the other lacks (genuine union)
    assert "alpha" in toks_a and "alpha" in toks_union and "alpha" not in toks_b
    assert "beta" in toks_b and "beta" in toks_union and "beta" not in toks_a
