"""scan_corpus discovery — which files become modules."""
from __future__ import annotations

import subprocess
from pathlib import Path

from slop.scope import scan_corpus
from slop.scope.discover import source_files
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


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), "-c", "user.email=t@t", "-c", "user.name=t", *args],
                   check=True, capture_output=True)


def test_outside_git_every_directory_is_read_except_dot_git(tmp_path: Path):
    for rel in ("src.py", ".hidden/h.py", "node_modules/dep.py", ".git/g.py"):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text("def f():\n    return 1\n")
    paths = _module_paths(scan_corpus(tmp_path, config=None))
    assert {Path(p).relative_to(tmp_path).as_posix() for p in paths} == {
        "src.py", ".hidden/h.py", "node_modules/dep.py"}


def test_inside_git_gitignore_decides_and_untracked_files_count(tmp_path: Path):
    _git(tmp_path, "init", "-q")
    (tmp_path / ".gitignore").write_text("build/\n")
    for rel in ("tracked.py", "build/gen.py", "new.py", ".hidden/h.py"):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text("def f():\n    return 1\n")
    _git(tmp_path, "add", ".gitignore", "tracked.py")
    paths = _module_paths(scan_corpus(tmp_path, config=None))
    assert {Path(p).relative_to(tmp_path).as_posix() for p in paths} == {
        "tracked.py", "new.py", ".hidden/h.py"}


def test_a_file_deleted_from_disk_but_still_tracked_is_not_read(tmp_path: Path):
    _git(tmp_path, "init", "-q")
    (tmp_path / "gone.py").write_text("def f():\n    return 1\n")
    (tmp_path / "kept.py").write_text("def g():\n    return 2\n")
    _git(tmp_path, "add", ".")
    (tmp_path / "gone.py").unlink()
    assert {p.name for p in source_files(tmp_path)} == {"kept.py"}


def test_exclude_still_applies_on_top_of_discovery(tmp_path: Path):
    (tmp_path / "a.py").write_text("def f():\n    return 1\n")
    (tmp_path / "vendor").mkdir()
    (tmp_path / "vendor" / "v.py").write_text("def g():\n    return 2\n")
    from slop.config import AnalysisConfig
    from slop.rules import RULE_REGISTRY
    (tmp_path / ".slop.toml").write_text('exclude = ["vendor/**"]\n')
    config = AnalysisConfig.load(tmp_path, RULE_REGISTRY)
    paths = _module_paths(scan_corpus(tmp_path, config))
    assert {Path(p).name for p in paths} == {"a.py"}
