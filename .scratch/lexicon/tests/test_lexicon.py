"""Tests for ``Lexicon``: queries, filtering, caching, composition."""
from __future__ import annotations

from collections import Counter

from scratch.lexicon import Lexeme, Lexicon, UNIVERSAL_NOISE


def _lex(*names: str) -> list[Lexeme]:
    return [Lexeme.of(n) for n in names]


class TestConstructionAndShape:
    def test_empty_lexicon_has_zero_length(self):
        assert len(Lexicon([])) == 0

    def test_length_matches_input(self):
        lexicon = Lexicon(_lex("a", "b", "c"))
        assert len(lexicon) == 3

    def test_iterates_in_input_order(self):
        items = _lex("first", "second", "third")
        lexicon = Lexicon(items)
        assert list(lexicon) == items


class TestFrequencies:
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
        # Excluding tokens that aren't in the bag is a no-op.
        assert lexicon.frequencies(exclude=frozenset({"foo"})) == Counter(
            {"get": 1, "user": 1},
        )

    def test_empty_lexicon_returns_empty_counter(self):
        assert Lexicon([]).frequencies() == Counter()


class TestModalTokens:
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
        # Strip the verbs; "user" rises to the top.
        modal = lexicon.modal_tokens(
            k=1,
            exclude=frozenset({"get", "set", "delete"}),
        )
        assert modal == {"user"}

    def test_k_larger_than_vocab_returns_all(self):
        lexicon = Lexicon(_lex("foo_bar"))
        assert lexicon.modal_tokens(k=10) == {"foo", "bar"}


class TestAlphabet:
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
        # An empty Lexeme contributes nothing to the alphabet.
        lexicon = Lexicon([Lexeme.of(""), Lexeme.of("foo_bar")])
        assert lexicon.alphabet("prefix") == Counter({"foo": 1})

    def test_exclude_affects_position(self):
        # If "extract" is excluded, the next surviving token becomes prefix.
        lexicon = Lexicon(_lex("extract_python", "extract_java"))
        alpha = lexicon.alphabet("prefix", exclude=frozenset({"extract"}))
        assert alpha == Counter({"python": 1, "java": 1})


class TestCoverage:
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


class TestOverlap:
    def test_full_overlap(self):
        lexicon = Lexicon(_lex("get_user_email"))
        target = Lexeme.of("get_user_email")
        assert lexicon.overlap(target, {"get", "user", "email"}) == 1.0

    def test_partial_overlap(self):
        lexicon = Lexicon(_lex("get_user_email"))
        target = Lexeme.of("get_user_email")
        # Only "get" hits the modal set; 1/3 of target's tokens.
        assert lexicon.overlap(target, {"get"}) == 1 / 3

    def test_empty_lexeme_yields_zero(self):
        lexicon = Lexicon([])
        empty = Lexeme.of("")
        assert lexicon.overlap(empty, {"foo"}) == 0.0

    def test_exclude_strips_target_tokens_before_overlap(self):
        lexicon = Lexicon([])
        target = Lexeme.of("get_user_email")
        # After stripping "get", remaining = {user, email}; modal = {get, user};
        # intersection = {user}, denominator = 2.
        assert lexicon.overlap(
            target,
            {"get", "user"},
            exclude=frozenset({"get"}),
        ) == 0.5


class TestCaching:
    def test_repeated_query_with_same_exclude_reuses_filtered_view(self):
        lexicon = Lexicon(_lex("get_user", "get_email"))
        ex = frozenset({"get"})
        first = lexicon._filtered(ex)
        second = lexicon._filtered(ex)
        # Identity check: cached, not recomputed.
        assert first is second

    def test_distinct_excludes_get_distinct_cache_entries(self):
        lexicon = Lexicon(_lex("get_user", "get_email"))
        ex_a = frozenset({"get"})
        ex_b = frozenset({"user"})
        view_a = lexicon._filtered(ex_a)
        view_b = lexicon._filtered(ex_b)
        assert view_a is not view_b


class TestComposition:
    def test_concatenated_items_form_valid_lexicon(self):
        a = _lex("alpha_one", "alpha_two")
        b = _lex("beta_one")
        merged = Lexicon(a + b)
        assert len(merged) == 3
        freq = merged.frequencies()
        assert freq["alpha"] == 2
        assert freq["beta"] == 1
        assert freq["one"] == 2


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
        # Smoke test: real exclude path with the shipped constant.
        lexicon = Lexicon(_lex(
            "get_user_id", "fetch_user_id", "delete_user_id",
        ))
        # "id" is in Newman 14; gets stripped under UNIVERSAL_NOISE.
        freq = lexicon.frequencies(exclude=UNIVERSAL_NOISE)
        assert "id" not in freq
        assert freq["user"] == 3
