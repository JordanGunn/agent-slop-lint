"""hotspots classifies churn against the files that actually changed in the window."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from slop.metrics.structural.view import Structure
from slop.scope import scan_corpus


def _git(root: Path, *args: str, date: str | None = None) -> None:
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    if date:
        env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = date
    subprocess.run(["git", "-C", str(root), *args], check=True, env=env, capture_output=True)


def _repo(root: Path) -> None:
    """Eight files of rising complexity, committed long ago."""
    _git(root, "init", "-q")
    for i in range(8):
        body = "def f(x):\n" + "".join(f"    if x == {k}:\n        return {k}\n" for k in range(i + 1))
        (root / f"m{i}.py").write_text(body + "    return 0\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "old", date="2020-01-01T00:00:00")


def _quadrants(root: Path) -> dict[str, str]:
    rows = Structure.over(scan_corpus(root, config=None)).hotspots(since="1 day ago")
    return {Path(h.path).name: h.quadrant for h in rows}


def test_no_churn_in_the_window_means_no_hotspot(tmp_path: Path):
    # The 75th-percentile churn cutoff is 0 here, and "churn >= 0" used to make every
    # complex file a hotspot ("High-churn" about files that did not change at all).
    _repo(tmp_path)
    assert "hotspot" not in _quadrants(tmp_path).values()


def test_only_the_file_that_changed_in_the_window_can_be_a_hotspot(tmp_path: Path):
    _repo(tmp_path)
    worst = tmp_path / "m7.py"
    worst.write_text(worst.read_text() + "".join(f"# churn {n}\n" for n in range(30)))
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "recent")
    quadrants = _quadrants(tmp_path)
    assert quadrants["m7.py"] == "hotspot"
    assert [n for n, q in quadrants.items() if q == "hotspot"] == ["m7.py"]


def test_churn_in_files_the_corpus_did_not_carve_is_not_ranked(tmp_path: Path):
    # A README with huge recent churn is not a complex code file and must not be ranked,
    # nor shift the cutoffs the real files are judged against.
    _repo(tmp_path)
    (tmp_path / "NOTES.md").write_text("".join(f"line {n}\n" for n in range(500)))
    worst = tmp_path / "m7.py"
    worst.write_text(worst.read_text() + "".join(f"# churn {n}\n" for n in range(30)))
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "recent")
    quadrants = _quadrants(tmp_path)
    assert "NOTES.md" not in quadrants
    assert [n for n, q in quadrants.items() if q == "hotspot"] == ["m7.py"]
