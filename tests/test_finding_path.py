"""Findings carry a root-relative ``path`` so same-named scopes can be told apart.

``component`` (the qualname) is unchanged: ``[ignore]`` entries and JSON consumers key on
it. The path is added beside it, never folded into it.
"""
from __future__ import annotations

import json
from pathlib import Path

from slop import cli

_FUNC = "def go(a):\n    if a:\n        return 1\n    return 0\n"
_CONFIG = '[rules."complexity.cyclomatic"]\nenabled = true\nthresholds.callable = 1\n'


def _project(root: Path, packages: tuple[str, ...]) -> Path:
    root.mkdir(parents=True)
    (root / ".slop.toml").write_text(_CONFIG)
    for name in packages:
        (root / name).mkdir()
        (root / name / "__init__.py").write_text("")
        (root / name / "mod.py").write_text(_FUNC)
    return root


def _lint(capsys, root: Path) -> dict:
    cli.main(["lint", "--root", str(root), "--output", "json"])
    return json.loads(capsys.readouterr().out)


def test_same_named_scopes_in_four_modules_get_four_distinct_locations(tmp_path: Path, capsys):
    root = _project(tmp_path / "proj", ("p1", "p2", "p3", "p4"))
    findings = [f for f in _lint(capsys, root)["findings"] if f["rule"] == "complexity.cyclomatic"]
    assert len(findings) == 4
    assert {f["component"] for f in findings} == {"mod.go"}          # qualname unchanged
    assert {f["path"] for f in findings} == {"p1/mod.py", "p2/mod.py", "p3/mod.py", "p4/mod.py"}


def test_paths_are_root_relative_so_json_is_identical_across_machines(tmp_path: Path, capsys):
    first = _lint(capsys, _project(tmp_path / "one", ("p1", "p2")))
    second = _lint(capsys, _project(tmp_path / "somewhere" / "else" / "two", ("p1", "p2")))
    assert first == second
    assert all(not str(f["path"]).startswith("/") for f in first["findings"] if f["path"])


def test_human_output_shows_where_each_finding_is(tmp_path: Path, capsys):
    root = _project(tmp_path / "proj", ("p1", "p2"))
    cli.main(["lint", "--root", str(root)])
    out = capsys.readouterr().out
    assert "mod.go  p1/mod.py" in out and "mod.go  p2/mod.py" in out
