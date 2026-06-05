"""metrics/lexical self-contained compute — affix patterns / FCA / packet filters.

These are pure algorithms (no AST/scope dependency), ported verbatim from the legacy
src/slop/lexicon. This pins their behaviour in the v3 tree before the view layer that
drives them lands.
"""
from __future__ import annotations

from slop.metrics.lexical import affix, filters
from slop.metrics.lexical.affix import Lexeme  # noqa: F401  (re-exported convenience)


def test_affix_patterns_group_token_edit_distance_1():
    # read_file / write_file / delete_file share the stem 'file' with a swapped verb.
    items = [Lexeme.of("read_file"), Lexeme.of("write_file"), Lexeme.of("delete_file")]
    patterns = affix.build_affix_patterns(items)
    assert patterns, "expected at least one affix pattern"
    # the swapped position holds the verb alphabet (the keys of variants)
    assert any({"read", "write", "delete"} <= set(p.variants) for p in patterns)


def test_compute_concepts_finds_shared_intent():
    # two entities sharing operations {open, close} form a closed concept.
    relation = {
        "FileA": {"open", "close", "read"},
        "FileB": {"open", "close", "write"},
    }
    concepts = affix.compute_concepts(relation)
    assert any(set(c.intent) >= {"open", "close"} and set(c.extent) >= {"FileA", "FileB"}
               for c in concepts)


def test_split_packets_by_class_ownership():
    packets = [{"open", "close", "read"}, {"foo", "bar", "baz"}]
    class_vocab = {"pkg.File": {"open", "close", "read", "seek"}}
    pathological, conventional = filters.split_packets_by_class_ownership(packets, class_vocab)
    assert {"foo", "bar", "baz"} in pathological
    assert any(p == {"open", "close", "read"} and qn == "pkg.File" for p, qn in conventional)


def test_universal_noise_excludes_newman_and_glue():
    assert "id" in affix.UNIVERSAL_NOISE and "the" in affix.UNIVERSAL_NOISE
