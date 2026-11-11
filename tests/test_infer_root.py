"""The project root, not the scan root, decides where rulings live and how findings are named."""
from __future__ import annotations

import json
import os
from pathlib import Path

from slop import cli
from slop.identity import project_path

TWO_GROUPS = "class A:\n    def f(self):\n        return self.a\n\n    def g(self):\n        return self.b\n"


def _project(root: Path, config: str | None = "") -> Path:
    """A project with the class in ``src/pkg/m.py``. ``config`` is the text of ``.slop.toml``, or None for none."""
    if config is not None:
        (root / ".slop.toml").write_text(config, encoding="utf-8")
    (root / "src" / "pkg").mkdir(parents=True)
    (root / "src" / "pkg" / "m.py").write_text(TWO_GROUPS, encoding="utf-8")
    return root / "src"


def _run(capsys, *argv: str) -> tuple[int, str]:
    capsys.readouterr()
    code = cli.main(list(argv))
    return code, capsys.readouterr().out


def _items(capsys, root: Path) -> list[dict]:
    """The residue of each finding that still needs a ruling, from `slop lint --output json`."""
    code, out = _run(capsys, "lint", "--root", str(root), "--output", "json")
    assert code in (0, 1)
    doc = json.loads(out)
    return [f["residue"] for f in doc["violations"] + doc["warnings"]
            if "residue" in f and f["residue"]["status"] in ("none", "stale")]


def _rule(capsys, root: Path, outcome: str, scan_root: Path) -> int:
    item = _items(capsys, root)[0]
    document = (root if root.is_dir() else root.parent) / "verdicts.json"
    document.write_text(json.dumps({"version": "1", "verdicts": [
        {"id": item["id"], "outcome": outcome, "reason": "because"}]}), encoding="utf-8")
    code, _ = _run(capsys, "infer", "apply", str(document), "--root", str(scan_root))
    return code


def test_a_finding_has_the_same_id_and_path_whichever_directory_is_scanned(tmp_path: Path, capsys):
    src = _project(tmp_path)
    [from_project], [from_src] = _items(capsys, tmp_path), _items(capsys, src)
    assert from_project["id"] == from_src["id"]
    assert from_project["locations"] == from_src["locations"]
    assert from_project["locations"][0]["path"] == "src/pkg/m.py"


def test_a_relative_scan_root_and_a_file_scan_root_name_the_finding_the_same_way(tmp_path: Path, capsys, monkeypatch):
    src = _project(tmp_path)
    [expected] = _items(capsys, tmp_path)
    monkeypatch.chdir(src)
    assert _items(capsys, Path("."))[0]["id"] == expected["id"]
    assert _items(capsys, src / "pkg" / "m.py")[0]["id"] == expected["id"]


def test_a_ruling_applied_under_one_root_holds_under_another(tmp_path: Path, capsys):
    src = _project(tmp_path)
    assert _rule(capsys, tmp_path, "confirm", scan_root=src) == 0          # ruled while scanning src/
    assert (tmp_path / ".slop" / "inferences.jsonl").is_file()              # stored at the project root
    assert not (src / ".slop").exists()
    for scan_root in (tmp_path, src):
        code, out = _run(capsys, "lint", "--root", str(scan_root))
        assert code == 1 and "[confirmed: because]" in out, scan_root
    assert _items(capsys, tmp_path) == [] and _items(capsys, src) == []


def test_the_pyproject_table_marks_the_project_root_too(tmp_path: Path, capsys):
    (tmp_path / "pyproject.toml").write_text("[tool.slop]\n", encoding="utf-8")
    src = _project(tmp_path, config=None)
    assert _rule(capsys, tmp_path, "clear", scan_root=src) == 0
    assert (tmp_path / ".slop" / "inferences.jsonl").is_file() and not (src / ".slop").exists()


def test_with_no_config_the_scan_root_is_the_project_root(tmp_path: Path, capsys):
    src = _project(tmp_path, config=None)
    assert _rule(capsys, src, "clear", scan_root=src) == 0
    assert (src / ".slop" / "inferences.jsonl").is_file() and not (tmp_path / ".slop").exists()
    assert _items(capsys, src) == []


def test_with_no_config_a_file_as_the_scan_root_makes_its_directory_the_project_root(tmp_path: Path, capsys):
    src = _project(tmp_path, config=None)
    module = src / "pkg" / "m.py"
    [item] = _items(capsys, module)
    assert item["locations"][0]["path"] == "m.py"              # relative to the file's directory
    assert _rule(capsys, module, "clear", scan_root=module) == 0
    assert (module.parent / ".slop" / "inferences.jsonl").is_file()


def test_project_path_agrees_across_spellings_and_symlinks(tmp_path: Path, monkeypatch):
    root = tmp_path / "proj"
    (root / "pkg").mkdir(parents=True)
    target = root / "pkg" / "m.py"
    target.write_text("x\n", encoding="utf-8")
    link = tmp_path / "link"
    os.symlink(root, link)
    monkeypatch.chdir(root)
    assert {project_path(target, root), project_path(link / "pkg" / "m.py", root),
            project_path("pkg/m.py", root), project_path(str(target), link)} == {"pkg/m.py"}


def test_a_path_outside_the_root_stays_absolute(tmp_path: Path):
    root = tmp_path / "proj"
    root.mkdir()
    elsewhere = tmp_path / "other" / "x.py"
    elsewhere.parent.mkdir()
    elsewhere.write_text("x\n", encoding="utf-8")
    assert project_path(elsewhere, root) == elsewhere.resolve().as_posix()


def test_the_lint_output_alone_locates_every_finding_and_its_code_from_any_directory(tmp_path: Path, capsys, monkeypatch):
    _project(tmp_path)
    monkeypatch.chdir(tmp_path)
    code, out = _run(capsys, "lint", "--root", "src", "--output", "json")    # a relative root, as typed
    doc = json.loads(out)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)                                             # read later, from another directory
    assert code == 0 and Path(doc["root"]).is_absolute() and Path(doc["project_root"]).is_absolute()
    [finding] = doc["warnings"]
    assert (Path(doc["root"]) / finding["path"]).is_file()                 # a finding's path: from root
    residue = finding["residue"]
    [where] = residue["locations"]
    lines = (Path(doc["project_root"]) / where["path"]).read_text(encoding="utf-8").splitlines()
    assert "\n".join(lines[where["first_line"] - 1:where["last_line"]]) == TWO_GROUPS.rstrip("\n")
