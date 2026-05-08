"""Tests for ``Lexeme`` + ``Lexicon`` + ``UNIVERSAL_NOISE``.

The substrate the four group-B lexical rules consume. Coverage:

- Lexeme: tokenisation contract, frozen-ness, hashability, metadata
- Lexicon: empty/populated, frequencies/modal/alphabet/coverage/overlap
  with and without ``exclude=``, instance-cached filtered view,
  composition by concatenation
- UNIVERSAL_NOISE: contains Newman 14, excludes hammers' banlist,
  excludes Python idioms (per backlog 09)
"""
from __future__ import annotations

from collections import Counter

import pytest

from slop._lexical._words import Lexeme, Lexicon, UNIVERSAL_NOISE


def _lex(*names: str) -> list[Lexeme]:
    return [Lexeme.of(n) for n in names]


# ---------------------------------------------------------------------------
# Lexeme
# ---------------------------------------------------------------------------


class TestLexemeConstruction:
    def test_snake_case_splits_on_underscore(self):
        lex = Lexeme.of("get_user_email")
        assert lex.text == "get_user_email"
        assert lex.tokens == ("get", "user", "email")
        assert lex.lower == ("get", "user", "email")

    def test_camel_case_splits_at_lower_upper_boundary(self):
        lex = Lexeme.of("processData")
        assert lex.tokens == ("process", "Data")
        assert lex.lower == ("process", "data")

    def test_acronym_then_word_keeps_acronym_intact(self):
        lex = Lexeme.of("HTTPClient")
        assert lex.tokens == ("HTTP", "Client")
        assert lex.lower == ("http", "client")

    def test_dunder_strips_leading_and_trailing_underscores(self):
        lex = Lexeme.of("__init__")
        assert lex.tokens == ("init",)

    def test_single_letter_passes_through(self):
        lex = Lexeme.of("x")
        assert lex.tokens == ("x",)
        assert lex.lower == ("x",)

    def test_empty_string_yields_no_tokens(self):
        lex = Lexeme.of("")
        assert lex.tokens == ()
        assert lex.lower == ()

    def test_mixed_snake_and_camel(self):
        lex = Lexeme.of("get_HTTPClient_url")
        assert lex.tokens == ("get", "HTTP", "Client", "url")
        assert lex.lower == ("get", "http", "client", "url")

    def test_digits_act_as_separators(self):
        lex = Lexeme.of("attempt_2_v3")
        assert lex.tokens == ("attempt", "v")


class TestLexemeMetadata:
    def test_file_and_line_default_to_none(self):
        lex = Lexeme.of("foo")
        assert lex.file is None
        assert lex.line is None

    def test_file_and_line_pass_through(self):
        lex = Lexeme.of("foo", file="bar.py", line=42)
        assert lex.file == "bar.py"
        assert lex.line == 42


class TestLexemeImmutability:
    def test_frozen_dataclass_rejects_mutation(self):
        lex = Lexeme.of("foo")
        with pytest.raises(Exception):
            lex.text = "bar"  # type: ignore[misc]

    def test_hashable(self):
        lex_a = Lexeme.of("foo")
        lex_b = Lexeme.of("foo")
        assert hash(lex_a) == hash(lex_b)
        assert {lex_a, lex_b} == {lex_a}

    def test_distinct_text_produces_distinct_hash(self):
        a = Lexeme.of("foo")
        b = Lexeme.of("bar")
        assert hash(a) != hash(b)

    def test_metadata_distinguishes_otherwise_equal_lexemes(self):
        a = Lexeme.of("foo", file="x.py", line=1)
        b = Lexeme.of("foo", file="y.py", line=2)
        assert a != b
        assert hash(a) != hash(b)


# ---------------------------------------------------------------------------
# Lexicon
# ---------------------------------------------------------------------------


class TestLexiconShape:
    def test_empty_lexicon_has_zero_length(self):
        assert len(Lexicon([])) == 0

    def test_length_matches_input(self):
        lexicon = Lexicon(_lex("a", "b", "c"))
        assert len(lexicon) == 3

    def test_iterates_in_input_order(self):
        items = _lex("first", "second", "third")
        lexicon = Lexicon(items)
        assert list(lexicon) == items


class TestLexiconFrequencies:
    def test_no_exclude_counts_every_token(self):
        lexicon = Lexicon(_lex("get_user", "get_email", "set_user"))
        freq = lexicon.frequencies()
        assert freq == Counter({"get": 2, "user": 2, "set": 1, "email": 1})

    def test_exclude_drops_listed_tokens(self):
        lexicon = Lexicon(_lex("get_user", "get_email", "set_user"))
        freq = lexicon.frequencies(exclude=frozenset({"get", "set"}))
        assert freq == Counter({"user": 2, "email": 1})

    def test_exclude_does_not_affect_unrelated_tokens(self):
        lexicon = Lexicon(_lex("get_user"))
        assert lexicon.frequencies(exclude=frozenset({"foo"})) == Counter(
            {"get": 1, "user": 1},
        )

    def test_empty_lexicon_returns_empty_counter(self):
        assert Lexicon([]).frequencies() == Counter()


class TestLexiconModalTokens:
    def test_returns_top_k_by_frequency(self):
        lexicon = Lexicon(_lex(
            "get_user", "get_email", "get_name",
            "set_user", "delete_user",
        ))
        modal = lexicon.modal_tokens(k=2)
        assert modal == {"get", "user"}

    def test_excludes_apply_before_ranking(self):
        lexicon = Lexicon(_lex(
            "get_user", "get_email", "get_name",
            "set_user", "delete_user",
        ))
        modal = lexicon.modal_tokens(
            k=1,
            exclude=frozenset({"get", "set", "delete"}),
        )
        assert modal == {"user"}

    def test_k_larger_than_vocab_returns_all(self):
        lexicon = Lexicon(_lex("foo_bar"))
        assert lexicon.modal_tokens(k=10) == {"foo", "bar"}


class TestLexiconAlphabet:
    def test_prefix_alphabet_counts_first_token(self):
        lexicon = Lexicon(_lex(
            "extract_python", "extract_java", "extract_csharp",
            "format_python",
        ))
        alpha = lexicon.alphabet("prefix")
        assert alpha == Counter({"extract": 3, "format": 1})

    def test_suffix_alphabet_counts_last_token(self):
        lexicon = Lexicon(_lex(
            "extract_python", "format_python",
            "extract_java",
        ))
        alpha = lexicon.alphabet("suffix")
        assert alpha == Counter({"python": 2, "java": 1})

    def test_empty_tokens_skipped(self):
        lexicon = Lexicon([Lexeme.of(""), Lexeme.of("foo_bar")])
        assert lexicon.alphabet("prefix") == Counter({"foo": 1})

    def test_exclude_affects_position(self):
        lexicon = Lexicon(_lex("extract_python", "extract_java"))
        alpha = lexicon.alphabet("prefix", exclude=frozenset({"extract"}))
        assert alpha == Counter({"python": 1, "java": 1})


class TestLexiconCoverage:
    def test_full_coverage(self):
        lexicon = Lexicon(_lex(
            "extract_python", "extract_java", "extract_rust",
        ))
        cov = lexicon.coverage({"python", "java", "rust"}, "suffix")
        assert cov == 1.0

    def test_partial_coverage(self):
        lexicon = Lexicon(_lex(
            "extract_python", "extract_java", "format_csv",
        ))
        cov = lexicon.coverage({"python", "java"}, "suffix")
        assert cov == 2 / 3

    def test_empty_lexicon_has_zero_coverage(self):
        assert Lexicon([]).coverage({"x"}, "prefix") == 0.0

    def test_alpha_disjoint_from_lexicon(self):
        lexicon = Lexicon(_lex("foo_bar"))
        assert lexicon.coverage({"baz"}, "prefix") == 0.0


class TestLexiconOverlap:
    def test_full_overlap(self):
        lexicon = Lexicon(_lex("get_user_email"))
        target = Lexeme.of("get_user_email")
        assert lexicon.overlap(target, {"get", "user", "email"}) == 1.0

    def test_partial_overlap(self):
        lexicon = Lexicon(_lex("get_user_email"))
        target = Lexeme.of("get_user_email")
        assert lexicon.overlap(target, {"get"}) == 1 / 3

    def test_empty_lexeme_yields_zero(self):
        lexicon = Lexicon([])
        empty = Lexeme.of("")
        assert lexicon.overlap(empty, {"foo"}) == 0.0

    def test_exclude_strips_target_tokens_before_overlap(self):
        lexicon = Lexicon([])
        target = Lexeme.of("get_user_email")
        assert lexicon.overlap(
            target,
            {"get", "user"},
            exclude=frozenset({"get"}),
        ) == 0.5


class TestLexiconCaching:
    def test_repeated_query_with_same_exclude_reuses_filtered_view(self):
        lexicon = Lexicon(_lex("get_user", "get_email"))
        ex = frozenset({"get"})
        first = lexicon._filtered(ex)
        second = lexicon._filtered(ex)
        assert first is second

    def test_distinct_excludes_get_distinct_cache_entries(self):
        lexicon = Lexicon(_lex("get_user", "get_email"))
        ex_a = frozenset({"get"})
        ex_b = frozenset({"user"})
        view_a = lexicon._filtered(ex_a)
        view_b = lexicon._filtered(ex_b)
        assert view_a is not view_b


class TestLexiconComposition:
    def test_concatenated_items_form_valid_lexicon(self):
        a = _lex("alpha_one", "alpha_two")
        b = _lex("beta_one")
        merged = Lexicon(a + b)
        assert len(merged) == 3
        freq = merged.frequencies()
        assert freq["alpha"] == 2
        assert freq["beta"] == 1
        assert freq["one"] == 2


# ---------------------------------------------------------------------------
# UNIVERSAL_NOISE
# ---------------------------------------------------------------------------


class TestUniversalNoise:
    def test_contains_newman_14(self):
        for w in ("a", "length", "id", "pos", "start", "next", "str",
                  "key", "f", "x", "index", "p", "left", "result"):
            assert w in UNIVERSAL_NOISE

    def test_excludes_se_boilerplate(self):
        # These belong to lexical.hammers, not the universal noise set.
        for w in ("manager", "helper", "service", "util", "handler",
                  "wrapper", "factory"):
            assert w not in UNIVERSAL_NOISE

    def test_excludes_python_idioms(self):
        # Per backlog 09 — language idioms are deferred, not in Layer 1.
        for w in ("self", "cls", "args", "kwargs"):
            assert w not in UNIVERSAL_NOISE

    def test_lexicon_can_use_universal_noise_as_exclude(self):
        lexicon = Lexicon(_lex(
            "get_user_id", "fetch_user_id", "delete_user_id",
        ))
        # "id" is in Newman 14; gets stripped under UNIVERSAL_NOISE.
        freq = lexicon.frequencies(exclude=UNIVERSAL_NOISE)
        assert "id" not in freq
        assert freq["user"] == 3
