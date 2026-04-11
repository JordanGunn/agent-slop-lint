"""Tests for slop hotspots rule."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from slop.models import RuleConfig, SlopConfig
from slop.rules.hotspots import run_churn_weighted


def _git(repo: Path, *args: str, env: dict[str, str] | None = None) -> None:
    full_env = os.environ.copy()
    full_env.update({
        "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "test@test.com",
        "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "test@test.com",
    })
    if env:
        full_env.update(env)
    subprocess.run(["git", *args], cwd=repo, env=full_env, check=True, capture_output=True)


def _init_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    _git(path, "init", "-q", "-b", "main")
    _git(path, "config", "user.email", "test@test.com")
    _git(path, "config", "user.name", "Test")
    return path


def _commit(repo, files, msg, date):
    for rel, content in files.items():
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        (repo / rel).write_text(content)
        _git(repo, "add", rel)
    _git(repo, "commit", "-q", "-m", msg, env={"GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date})


_COMPLEX = "def f(a,b,c,d,e,f):\n" + "".join(f"    if {chr(97+i)}: pass\n" for i in range(6))


def test_hotspot_violation_when_complex_and_churned(tmp_path: Path):
    repo = _init_repo(tmp_path / "repo")
    _commit(repo, {"hot.py": _COMPLEX}, "c1", "2026-03-01T00:00:00+00:00")
    _commit(repo, {"hot.py": _COMPLEX + "\n# e1\n"}, "c2", "2026-03-02T00:00:00+00:00")
    _commit(repo, {"hot.py": _COMPLEX + "\n# e1\n# e2\n"}, "c3", "2026-03-03T00:00:00+00:00")
    # Need 8+ files with 2+ commits each for quadrant classification
    fillers = {f"filler{i}.py": f"def g{i}():\n    pass\n" for i in range(8)}
    _commit(repo, fillers, "fillers-1", "2026-03-04T00:00:00+00:00")
    fillers2 = {f"filler{i}.py": f"def g{i}():\n    return {i}\n" for i in range(8)}
    _commit(repo, fillers2, "fillers-2", "2026-03-05T00:00:00+00:00")

    rc = RuleConfig(enabled=True, severity="error", params={
        "since": "all", "min_commits": 2, "fail_on_quadrant": ["hotspot"],
    })
    result = run_churn_weighted(repo, rc, SlopConfig(root=str(repo)))
    # hot.py should be the hotspot (high ccx + high churn relative to fillers)
    hotspot_files = [v.file for v in result.violations]
    assert any("hot.py" in f for f in hotspot_files)


def test_hotspot_pass_when_no_hotspots(tmp_path: Path):
    repo = _init_repo(tmp_path / "repo")
    _commit(repo, {"a.py": "def f():\n    pass\n"}, "c1", "2026-03-01T00:00:00+00:00")
    _commit(repo, {"a.py": "def f():\n    return 1\n"}, "c2", "2026-03-02T00:00:00+00:00")
    rc = RuleConfig(enabled=True, severity="error", params={
        "since": "all", "min_commits": 2, "fail_on_quadrant": ["hotspot"],
    })
    result = run_churn_weighted(repo, rc, SlopConfig(root=str(repo)))
    # Too few files for quadrant classification — no violations
    assert result.status == "pass"


def test_hotspot_summary_includes_window(tmp_path: Path):
    repo = _init_repo(tmp_path / "repo")
    _commit(repo, {"a.py": "x = 1\n"}, "c1", "2026-03-01T00:00:00+00:00")
    rc = RuleConfig(enabled=True, severity="error", params={
        "since": "90 days ago", "min_commits": 1, "fail_on_quadrant": ["hotspot"],
    })
    result = run_churn_weighted(repo, rc, SlopConfig(root=str(repo)))
    assert "window_since" in result.summary
    assert result.summary["window_since"] == "90 days ago"
