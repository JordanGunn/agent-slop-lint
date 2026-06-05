"""Cross-rule corroboration index (rules/_battery) — correctness + memoisation.

imposters and slackers both build this index; it walks clone detection and every module's
redundancy, so it is memoised on the corpus AnalysisContext and shared across the run.
"""
from __future__ import annotations

from pathlib import Path

from slop.rules._battery import corroboration_groups, is_corroborated
from slop.scope import scan_corpus

_CLONE = (
    "    a = 1\n    b = a + 1\n    c = b * 2\n    d = c - 3\n    return d + a + b + c\n"
)


def test_is_corroborated_requires_two_overlapping_members():
    groups = [frozenset({"alpha", "beta", "gamma"})]
    assert is_corroborated({"alpha", "beta"}, groups)       # two members in one group
    assert not is_corroborated({"alpha"}, groups)            # one is not enough
    assert not is_corroborated({"alpha", "zeta"}, groups)    # only one overlaps


def test_clone_family_becomes_a_corroboration_group(tmp_path: Path):
    (tmp_path / "a.py").write_text(f"def one():\n{_CLONE}")
    (tmp_path / "b.py").write_text(f"def two():\n{_CLONE}")
    corpus = scan_corpus(tmp_path, config=None)
    groups = corroboration_groups(corpus)
    assert any({"one", "two"} <= g for g in groups)


def test_index_is_memoised_on_the_context(tmp_path: Path):
    (tmp_path / "m.py").write_text("def f(x):\n    return x + 1\n")
    corpus = scan_corpus(tmp_path, config=None)
    first = corroboration_groups(corpus)
    assert ("corroboration_groups", 10) in corpus.context.cache
    assert corroboration_groups(corpus) is first   # second call hits the memo
