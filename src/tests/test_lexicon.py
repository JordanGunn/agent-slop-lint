"""Tests for ``Lexeme`` + ``UNIVERSAL_NOISE``.

The lightweight primitives shared between sprawl, slackers, and the
profile-cluster helper. The bag-of-Lexeme ``Lexicon`` class from the
v1.x ``_lexical/_words.py`` retired with the kernel sweep; its
modal-token + overlap arithmetic now lives inline in
``slop.lexicon.profile``.
"""
from __future__ import annotations

import pytest

from slop.lexicon.affix import Lexeme, UNIVERSAL_NOISE


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
        lex = Lexeme.of("my_processData")
        assert lex.tokens == ("my", "process", "Data")
        assert lex.lower == ("my", "process", "data")

    def test_digits_act_as_separators(self):
        lex = Lexeme.of("v2_handler")
        assert lex.tokens == ("v", "handler")


class TestLexemeMetadata:
    def test_file_and_line_default_to_none(self):
        lex = Lexeme.of("name")
        assert lex.file is None
        assert lex.line is None

    def test_file_and_line_pass_through(self):
        lex = Lexeme.of("name", file="src/x.py", line=42)
        assert lex.file == "src/x.py"
        assert lex.line == 42


class TestLexemeImmutability:
    def test_frozen_dataclass_rejects_mutation(self):
        lex = Lexeme.of("name")
        with pytest.raises(Exception):  # noqa: PT011
            lex.text = "other"  # type: ignore[misc]

    def test_hashable(self):
        a = Lexeme.of("name")
        b = Lexeme.of("name")
        assert hash(a) == hash(b)
        assert {a, b} == {a}

    def test_distinct_text_produces_distinct_hash(self):
        a = Lexeme.of("alpha")
        b = Lexeme.of("beta")
        assert hash(a) != hash(b)

    def test_metadata_distinguishes_otherwise_equal_lexemes(self):
        a = Lexeme.of("name", file="a.py", line=1)
        b = Lexeme.of("name", file="b.py", line=1)
        assert a != b


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
