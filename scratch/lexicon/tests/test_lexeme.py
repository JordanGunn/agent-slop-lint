"""Tests for ``Lexeme``: tokenisation contract, frozen-ness, hashability."""
from __future__ import annotations

import pytest

from scratch.lexicon import Lexeme


class TestConstruction:
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


class TestMetadata:
    def test_file_and_line_default_to_none(self):
        lex = Lexeme.of("foo")
        assert lex.file is None
        assert lex.line is None

    def test_file_and_line_pass_through(self):
        lex = Lexeme.of("foo", file="bar.py", line=42)
        assert lex.file == "bar.py"
        assert lex.line == 42


class TestImmutability:
    def test_frozen_dataclass_rejects_mutation(self):
        lex = Lexeme.of("foo")
        with pytest.raises(Exception):
            lex.text = "bar"  # type: ignore[misc]

    def test_hashable(self):
        lex_a = Lexeme.of("foo")
        lex_b = Lexeme.of("foo")
        # Same content → same hash; can be set members.
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
