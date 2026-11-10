"""hotspots: churn x complexity over a window of revisions, plus uncommitted changes."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from slop import cli
from slop.metrics.structural.view import Structure
from slop.scope import scan_corpus


def _git(root: Path, *args: str) -> None:
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    subprocess.run(["git", "-C", str(root), *args], check=True, env=env, capture_output=True)


def _body(branches: int) -> str:
    return "def f(x):\n" + "".join(f"    if x == {k}:\n        return {k}\n" for k in range(branches)) + "    return 0\n"


def _commit(root: Path, message: str) -> None:
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", message)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """Three commits: initial (simple.py, complex.py), then complex.py grows, then simple.py."""
    _git(tmp_path, "init", "-q")
    (tmp_path / "simple.py").write_text(_body(1))
    (tmp_path / "complex.py").write_text(_body(4))
    _commit(tmp_path, "initial")
    (tmp_path / "complex.py").write_text(_body(4) + "# a\n# b\n# c\n")
    _commit(tmp_path, "grow complex")
    (tmp_path / "simple.py").write_text(_body(1) + "# a\n")
    _commit(tmp_path, "touch simple")
    return tmp_path


def _rows(root: Path, **window) -> dict[str, tuple[int, int]]:
    rows = Structure.over(scan_corpus(root, config=None)).hotspots(**window)
    return {h.path: (h.churn, h.complexity) for h in rows}


def test_last_n_counts_only_the_commits_in_the_window(repo: Path):
    assert _rows(repo, last=1) == {"simple.py": (1, 2)}
    assert _rows(repo, last=2) == {"simple.py": (1, 2), "complex.py": (3, 5)}


def test_last_beyond_the_history_covers_all_of_it(repo: Path):
    assert _rows(repo, last=50) == {"complex.py": (13, 5), "simple.py": (5, 2)}


def test_since_a_revision_equals_the_same_span_as_last(repo: Path):
    assert _rows(repo, since="HEAD~2") == _rows(repo, last=2)


def test_since_head_is_only_what_is_uncommitted(repo: Path):
    assert _rows(repo, since="HEAD") == {}
    (repo / "complex.py").write_text(_body(4) + "# a\n# b\n# c\n# d\n# e\n")     # tracked edit
    (repo / "fresh.py").write_text("def g():\n    return 1\n\n\n")               # untracked, 4 lines
    assert _rows(repo, since="HEAD") == {"complex.py": (2, 5), "fresh.py": (4, 1)}


def test_untracked_ignored_files_and_uncarved_files_are_not_ranked(repo: Path):
    (repo / ".gitignore").write_text("skip.py\n")
    (repo / "skip.py").write_text("def g():\n    return 1\n")
    (repo / "NOTES.md").write_text("".join(f"line {n}\n" for n in range(500)))
    assert _rows(repo, since="HEAD") == {}


def test_hottest_first_by_churn_times_complexity(repo: Path):
    (repo / "aaa.py").write_text("x = 1\n")     # first alphabetically, coolest
    paths = list(_rows(repo, last=2))
    assert paths == ["complex.py", "simple.py", "aaa.py"]    # 3 x 5 = 15, 1 x 2 = 2, 1 x 0 = 0


def test_a_renamed_file_is_counted_under_its_new_name(repo: Path):
    _git(repo, "mv", "simple.py", "renamed.py")
    (repo / "renamed.py").write_text(_body(1) + "# a\n# b\n")
    rows = _rows(repo, since="HEAD")
    assert "renamed.py" in rows and "simple.py" not in rows


@pytest.mark.parametrize("window, message", [
    ({"since": "no-such-rev"}, "unknown revision"),
    ({"last": -1}, "0 or more"),
])
def test_a_bad_window_is_an_error(repo: Path, window, message):
    with pytest.raises(ValueError, match=message):
        _rows(repo, **window)


def test_outside_a_git_work_tree_it_is_an_error_not_an_empty_answer(tmp_path: Path):
    (tmp_path / "a.py").write_text(_body(1))
    with pytest.raises(ValueError, match="not a git work tree"):
        _rows(tmp_path)


def test_a_repository_with_no_commits_is_an_error(tmp_path: Path):
    _git(tmp_path, "init", "-q")
    (tmp_path / "a.py").write_text(_body(1))
    with pytest.raises(ValueError, match="no commits"):
        _rows(tmp_path)


def test_cli_json_and_exit_codes(repo: Path, capsys, tmp_path_factory):
    assert cli.main(["hotspots", "--root", str(repo), "--last", "2", "--output", "json"]) == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["window"] == "last 2 commits + uncommitted"
    assert doc["files"][0] == {"path": "complex.py", "churn": 3, "complexity": 5, "product": 15}
    plain = tmp_path_factory.mktemp("plain")
    (plain / "a.py").write_text(_body(1))
    assert cli.main(["hotspots", "--root", str(plain)]) == 2
    assert "not a git work tree" in capsys.readouterr().err
    with pytest.raises(SystemExit):
        cli.main(["hotspots", "--since", "HEAD", "--last", "3", "--root", str(repo)])
