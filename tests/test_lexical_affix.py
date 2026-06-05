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


def test_compute_concepts_wide_alphabet_is_fast():
    # Regression: the old brute force enumerated 2**len(attributes) subsets, so a wide
    # alphabet (here 40 stems, as occurs at corpus scope) ran ~2^40 iterations and hung
    # the linter. The meet-closure form is bounded by the actual concept count; this
    # relation has few concepts, so it must finish near-instantly.
    import time

    relation = {f"op_{i}": {f"a{i}", f"a{i + 1}", "shared"} for i in range(40)}
    start = time.perf_counter()
    concepts = affix.compute_concepts(relation)
    elapsed = time.perf_counter() - start
    assert elapsed < 2.0, f"compute_concepts took {elapsed:.1f}s on a 41-attribute relation"
    # the universally-shared op is a real concept (every object, intent ⊇ {shared})
    assert any("shared" in c.intent and len(c.extent) == 40 for c in concepts)


def test_compute_concepts_pathological_lattice_is_bounded():
    # A densely-overlapping relation can have exponentially many concepts; the backstop
    # returns empty rather than spinning. Keep it well under the cap to stay fast.
    relation = {f"o{i}": {f"a{b}" for b in range(18) if i & (1 << b)} for i in range(1, 2 ** 18, 7)}
    import time

    start = time.perf_counter()
    concepts = affix.compute_concepts(relation, max_concepts=5_000)
    assert time.perf_counter() - start < 5.0
    # either it stayed under the cap (real concepts) or it bailed to empty — never hangs
    assert isinstance(concepts, list)


def test_split_packets_by_class_ownership():
    packets = [{"open", "close", "read"}, {"foo", "bar", "baz"}]
    class_vocab = {"pkg.File": {"open", "close", "read", "seek"}}
    pathological, conventional = filters.split_packets_by_class_ownership(packets, class_vocab)
    assert {"foo", "bar", "baz"} in pathological
    assert any(p == {"open", "close", "read"} and qn == "pkg.File" for p, qn in conventional)


def test_universal_noise_excludes_newman_and_glue():
    assert "id" in affix.UNIVERSAL_NOISE and "the" in affix.UNIVERSAL_NOISE
