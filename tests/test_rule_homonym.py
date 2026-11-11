"""homonym: a class name defined more than once in a language is a subjective warning."""
from __future__ import annotations

import json
from pathlib import Path

from slop import cli
from slop.config import RuleConfig
from slop.rules.homonym import HomonymRule
from slop.scope import scan_corpus


def _files(root: Path, files: dict[str, str]) -> None:
    for name, text in files.items():
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_text(text, encoding="utf-8")


def _check(root: Path, limit: int = 1):
    return list(HomonymRule().check(scan_corpus(root, config=None),
                                    RuleConfig(name="homonym", options={"limit": limit})))


def test_a_name_defined_in_two_files_is_one_finding_at_its_first_definition(tmp_path: Path):
    _files(tmp_path, {"a/store.py": "class Store:\n    pass\n", "b/store.py": "class Store:\n    pass\n",
                      "c.py": "class Unique:\n    pass\n"})
    [v] = _check(tmp_path)
    assert (v.rule, v.subject, v.value, v.threshold) == ("homonym", "store.Store", 2, 1)
    assert v.path == str(tmp_path / "a" / "store.py") and v.line == 1
    assert "a/store.py:1 store.Store; b/store.py:1 store.Store" in v.message


def test_the_limit_is_how_many_definitions_a_name_may_have(tmp_path: Path):
    _files(tmp_path, {f"{p}/m.py": "class Key:\n    pass\n" for p in ("a", "b", "c")})
    assert [v.value for v in _check(tmp_path)] == [3]
    assert _check(tmp_path, limit=3) == []


def test_private_names_and_one_definition_per_language_are_not_homonyms(tmp_path: Path):
    _files(tmp_path, {"a.py": "class _Lines:\n    pass\n", "b.py": "class _Lines:\n    pass\n",
                      "c.py": "class Point:\n    pass\n", "d.ts": "class Point {}\n"})
    assert _check(tmp_path) == []


def test_lint_reports_it_as_a_warning_with_a_residue_to_rule_on(tmp_path: Path, capsys):
    _files(tmp_path, {"a/store.py": "class Store:\n    def get(self):\n        return 1\n",
                      "b/store.py": "class Store:\n    pass\n"})
    capsys.readouterr()
    assert cli.main(["lint", "--root", str(tmp_path), "--output", "json"]) == 0      # subjective: never fails
    [warning] = [w for w in json.loads(capsys.readouterr().out)["warnings"] if w["rule"] == "homonym"]
    residue = warning["residue"]
    assert (residue["subject"], residue["locations"][0]["first_line"], residue["locations"][0]["last_line"]) == ("store.Store", 1, 3)
    assert residue["rubric"]["command"] == "slop infer references rubrics/homonym"


def test_the_finding_names_its_scope_and_the_other_definitions(tmp_path: Path):
    _files(tmp_path, {"a/store.py": "class Store:\n    pass\n", "b/store.py": "class Store:\n    pass\n",
                      "c/store.py": "class Store:\n    pass\n"})
    [v] = _check(tmp_path)
    assert v.scope.qualname == "store.Store" and v.scope.spans[0].path == str(tmp_path / "a" / "store.py")
    assert [r.spans[0].path for r in v.related] == [str(tmp_path / p / "store.py") for p in ("b", "c")]
