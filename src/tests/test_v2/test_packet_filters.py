"""Tests for ``Structure.class_vocabularies`` and the packet-ownership filter."""
from __future__ import annotations

from pathlib import Path

from slop.lexicon.filters import split_packets_by_class_ownership
from slop.tree.tree import Tree


def _structure(root: Path):
    t = Tree(root)
    t.scan()
    return t.structure


def _write(root: Path, rel: str, src: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(src)
    return path


class TestClassVocabularies:
    def test_collects_method_tokens_per_class(self, tmp_path: Path):
        _write(tmp_path, "a.py",
               "class Animal:\n"
               "    def eat(self): pass\n"
               "    def sleep(self): pass\n"
               "class Vehicle:\n"
               "    def drive(self): pass\n"
               "    def park(self): pass\n")
        vocabs = _structure(tmp_path).class_vocabularies()
        # Two classes; each owns its method-name tokens (lowercased,
        # snake/Camel-split).
        animal_vocab = next(v for q, v in vocabs.items() if q.endswith("Animal"))
        vehicle_vocab = next(v for q, v in vocabs.items() if q.endswith("Vehicle"))
        assert animal_vocab == {"eat", "sleep"}
        assert vehicle_vocab == {"drive", "park"}

    def test_camelcase_method_names_split(self, tmp_path: Path):
        _write(tmp_path, "a.py",
               "class HTTPClient:\n"
               "    def parseRequest(self): pass\n"
               "    def sendResponse(self): pass\n")
        vocabs = _structure(tmp_path).class_vocabularies()
        v = next(iter(vocabs.values()))
        assert v == {"parse", "request", "send", "response"}

    def test_free_functions_excluded(self, tmp_path: Path):
        _write(tmp_path, "a.py",
               "def helper(): pass\n"
               "class Box:\n"
               "    def open(self): pass\n")
        vocabs = _structure(tmp_path).class_vocabularies()
        assert all("helper" not in v for v in vocabs.values())
        box_vocab = next(iter(vocabs.values()))
        assert box_vocab == {"open"}

    def test_empty_corpus_returns_empty(self, tmp_path: Path):
        assert _structure(tmp_path).class_vocabularies() == {}


class TestSplitPacketsByClassOwnership:
    def test_packet_subset_of_class_vocab_is_conventional(self):
        packets = [{"eat", "sleep"}]
        vocabs = {"pkg.Animal": {"eat", "sleep", "run"}}
        pathological, conventional = split_packets_by_class_ownership(packets, vocabs)
        assert pathological == []
        assert conventional == [({"eat", "sleep"}, "pkg.Animal")]

    def test_packet_not_in_any_class_is_pathological(self):
        packets = [{"excludes", "hidden", "ignore", "globs", "languages"}]
        vocabs = {"pkg.SomeClass": {"foo", "bar"}}
        pathological, conventional = split_packets_by_class_ownership(packets, vocabs)
        assert pathological == [{"excludes", "hidden", "ignore", "globs", "languages"}]
        assert conventional == []

    def test_packet_partial_overlap_is_pathological(self):
        # Packet has one token in the class vocab but others are foreign
        # — class doesn't own the whole packet, so it's pathological.
        packets = [{"a", "b", "c"}]
        vocabs = {"pkg.X": {"a", "b"}}
        pathological, conventional = split_packets_by_class_ownership(packets, vocabs)
        assert pathological == [{"a", "b", "c"}]
        assert conventional == []

    def test_first_matching_class_wins(self):
        packets = [{"foo"}]
        vocabs = {
            "pkg.B": {"foo", "bar"},
            "pkg.A": {"foo"},
        }
        pathological, conventional = split_packets_by_class_ownership(packets, vocabs)
        assert pathological == []
        # Sorted by qualname → pkg.A wins
        assert conventional == [({"foo"}, "pkg.A")]

    def test_empty_vocabs_returns_all_pathological(self):
        packets = [{"a", "b"}, {"c", "d"}]
        pathological, conventional = split_packets_by_class_ownership(packets, {})
        assert len(pathological) == 2
        assert conventional == []

    def test_empty_packets_returns_empty(self):
        pathological, conventional = split_packets_by_class_ownership(
            [], {"X": {"a", "b"}},
        )
        assert pathological == []
        assert conventional == []


class TestEndToEnd:
    def test_dispatch_family_class_filters_out_packet(self, tmp_path: Path):
        # A class with methods red/green/yellow/blue + a free-function
        # cluster also taking text. The free-function cluster forms a
        # packet that is conventional because Color owns {red, green,
        # yellow, blue}.
        _write(tmp_path, "color.py",
               "class Color:\n"
               "    def red(self, text): pass\n"
               "    def green(self, text): pass\n"
               "    def yellow(self, text): pass\n"
               "    def blue(self, text): pass\n")
        from slop.tree.tree import Tree
        t = Tree(tmp_path)
        t.scan()
        # Just the four method-name tokens form a packet for this test.
        packet = {"red", "green", "yellow", "blue"}
        vocabs = t.structure.class_vocabularies()
        pathological, conventional = split_packets_by_class_ownership([packet], vocabs)
        # The Color class owns the whole packet → conventional.
        assert pathological == []
        assert len(conventional) == 1
        assert conventional[0][0] == packet
        assert conventional[0][1].endswith("Color")
