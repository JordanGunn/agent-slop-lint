"""Tests for ``slop.lexicon.actions`` — packet → corrective-action mapping."""
from __future__ import annotations

from pathlib import Path

from slop.lexicon.actions import (
    CorrectiveAction,
    map_packet,
    map_packets_to_actions,
)
from slop.tree.tree import Tree


def _write(root: Path, rel: str, src: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(src)
    return path


def _lexicon(root: Path):
    t = Tree(root)
    t.scan()
    return t.lexicon


class TestExtractDataclass:
    def test_five_param_packet_high_confidence(self, tmp_path: Path):
        _write(tmp_path, "a.py",
               "def f(excludes, hidden, ignore, globs, languages): pass\n"
               "def g(excludes, hidden, ignore, globs, languages): pass\n")
        lex = _lexicon(tmp_path)
        action = map_packet(
            {"excludes", "hidden", "ignore", "globs", "languages"},
            lex, scope="callable",
        )
        assert action.kind == "extract_dataclass"
        assert action.confidence == "high"
        assert "dataclass" in action.advisory.lower()
        assert action.evidence["provenance"] == "all_param"


class TestNamedTuple:
    def test_two_param_pair_medium_confidence(self, tmp_path: Path):
        _write(tmp_path, "a.py",
               "def f(since, until): pass\n"
               "def g(since, until): pass\n")
        lex = _lexicon(tmp_path)
        action = map_packet({"since", "until"}, lex, scope="callable")
        assert action.kind == "named_tuple"
        assert action.confidence == "medium"


class TestExtractModule:
    def test_three_name_only_file_scope_high_confidence(self, tmp_path: Path):
        # Tokens appear only as function-name tokens, never as params.
        _write(tmp_path, "a.py",
               "def parse_pdf_extract(): pass\n"
               "def render_pdf_extract(): pass\n")
        _write(tmp_path, "b.py",
               "def export_pdf_extract(): pass\n")
        lex = _lexicon(tmp_path)
        action = map_packet(
            {"pdf", "extract", "parse"}, lex, scope="file",
        )
        assert action.kind == "extract_module"
        assert action.confidence == "high"
        assert action.evidence["provenance"] == "all_name"


class TestMissingClass:
    def test_mixed_packet_file_scope(self, tmp_path: Path):
        # Tokens appear both as names AND as params, file scope.
        _write(tmp_path, "a.py",
               "def render(customer): pass\n"
               "class Customer:\n    pass\n"
               "def parse(customer): pass\n")
        lex = _lexicon(tmp_path)
        action = map_packet(
            {"customer", "parse", "render"}, lex, scope="file",
        )
        assert action.kind == "missing_class"
        assert action.evidence["provenance"] == "mixed"


class TestNamingConvention:
    def test_mixed_packet_callable_scope(self, tmp_path: Path):
        # The classic run_X(config) returning Slop registry convention.
        _write(tmp_path, "a.py",
               "def run_alpha(config): pass\n"
               "def run_beta(config): pass\n"
               "def run_gamma(config): pass\n")
        lex = _lexicon(tmp_path)
        action = map_packet(
            {"run", "config"}, lex, scope="callable",
        )
        assert action.kind == "naming_convention"
        assert action.confidence == "medium"


class TestReviewFallback:
    def test_unmatched_shape_returns_review(self, tmp_path: Path):
        # An empty corpus — provenance is none.
        action = map_packet(
            {"foo", "bar"}, _lexicon(tmp_path), scope="callable",
        )
        assert action.kind == "review"
        assert action.confidence == "low"


class TestBatchMapping:
    def test_map_packets_to_actions_returns_one_per_packet(self, tmp_path: Path):
        _write(tmp_path, "a.py",
               "def f(excludes, hidden, ignore, globs, languages): pass\n"
               "def g(excludes, hidden, ignore, globs, languages): pass\n"
               "def h(since, until): pass\n"
               "def i(since, until): pass\n")
        lex = _lexicon(tmp_path)
        actions = map_packets_to_actions([
            {"excludes", "hidden", "ignore", "globs", "languages"},
            {"since", "until"},
        ], lex, scope="callable")
        assert len(actions) == 2
        assert {a.kind for a in actions} == {"extract_dataclass", "named_tuple"}


class TestCorrectiveActionDict:
    def test_as_dict_is_json_friendly(self, tmp_path: Path):
        import json
        _write(tmp_path, "a.py", "def f(a, b): pass\ndef g(a, b): pass\n")
        lex = _lexicon(tmp_path)
        action = map_packet({"a", "b"}, lex, scope="callable")
        d = action.as_dict()
        s = json.dumps(d)
        assert "packet" in d
        assert "kind" in d
        assert "advisory" in d
        assert len(s) > 0
