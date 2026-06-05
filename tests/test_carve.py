"""scan_corpus discovery — which files become modules."""
from __future__ import annotations

from pathlib import Path

from slop.scope import scan_corpus
from slop.scope.identity import ScopeKind


def _module_paths(corpus) -> set[str]:
    stack = [corpus]
    out: set[str] = set()
    while stack:
        c = stack.pop()
        if c.id.kind is ScopeKind.MODULE and c.id.spans:
            out.add(c.id.spans[0].path)
        stack.extend(c.children())
    return out


def test_hidden_directories_are_skipped(tmp_path: Path):
    # Source under a hidden dir (a vendored snapshot, scratch, a cache) must not be
    # carved — slop lints the project, not its .internal/.scratch detritus.
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "real.py").write_text("def f():\n    return 1\n")
    (tmp_path / ".scratch").mkdir()
    (tmp_path / ".scratch" / "copy.py").write_text("def g():\n    return 2\n")
    (tmp_path / "docs" / ".internal").mkdir(parents=True)
    (tmp_path / "docs" / ".internal" / "old.py").write_text("def h():\n    return 3\n")

    paths = _module_paths(scan_corpus(tmp_path, config=None))
    assert any(p.endswith("real.py") for p in paths)
    assert not any(".scratch" in p for p in paths)
    assert not any(".internal" in p for p in paths)


def test_named_skip_dirs_still_skipped(tmp_path: Path):
    (tmp_path / "src.py").write_text("def f():\n    return 1\n")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "dep.py").write_text("def g():\n    return 2\n")
    paths = _module_paths(scan_corpus(tmp_path, config=None))
    assert any(p.endswith("src.py") for p in paths)
    assert not any("node_modules" in p for p in paths)
