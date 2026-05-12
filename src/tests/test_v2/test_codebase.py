"""Tests for ``slop.tree.tree.Tree``."""
from __future__ import annotations

from pathlib import Path

import pytest

from slop.tree.tree import Tree


class TestCodebaseConstruction:
    def test_constructs_without_scanning(self, tmp_path: Path):
        cb = Tree(tmp_path)
        assert cb.root == tmp_path

    def test_views_unavailable_before_scan(self, tmp_path: Path):
        cb = Tree(tmp_path)
        with pytest.raises(RuntimeError):
            cb.structure  # noqa: B018
        with pytest.raises(RuntimeError):
            cb.lexicon  # noqa: B018
        with pytest.raises(RuntimeError):
            cb.languages_detected  # noqa: B018


class TestCodebaseScan:
    def test_scan_populates_parses(self, tiny_corpus: Path):
        cb = Tree(tiny_corpus)
        cb.scan()
        assert len(cb._parses) == 2  # a.py + b.py

    def test_scan_is_idempotent(self, tiny_corpus: Path):
        cb = Tree(tiny_corpus)
        cb.scan()
        n = len(cb._parses)
        cb.scan()
        assert len(cb._parses) == n  # second call no-ops

    def test_languages_detected_includes_python(self, tiny_corpus: Path):
        cb = Tree(tiny_corpus)
        cb.scan()
        assert "python" in cb.languages_detected

    def test_polyglot_languages_detected(self, polyglot_corpus: Path):
        cb = Tree(polyglot_corpus)
        cb.scan()
        detected = set(cb.languages_detected)
        assert {"python", "javascript", "typescript", "go", "rust", "ruby", "c"}.issubset(detected)

    def test_excludes_filter_files_out(self, tiny_corpus: Path):
        cb = Tree(tiny_corpus, excludes=("**/a.py",))
        cb.scan()
        assert len(cb._parses) == 1  # only b.py
