"""Agglomerations (Oizumi et al. 2016): findings grouped by the structure that relates them."""
from __future__ import annotations

from pathlib import Path

from slop.agglomeration import Topology, agglomerate
from slop.cli.lint import analyse


def _groups(tmp_path: Path, files: dict[str, str]) -> list[tuple[str, str, list[str]]]:
    for name, text in files.items():
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text(text, encoding="utf-8")
    analysis = analyse(tmp_path)
    groups = agglomerate([*analysis.report.violations, *analysis.report.warnings], analysis.corpus)
    return [(g.topology.value, g.lead.qualname, sorted(f.rule for f in g.findings)) for g in groups]


_TANGLED = "    if a == {i}:\n        b {op}= {i}\n"


def _tangled(name: str, extra: str = "", op: str = "+") -> str:
    """A function over every complexity limit; ``op`` keeps two of them from being clones."""
    return f"def {name}(a, b):\n{extra}" + "".join(_TANGLED.format(i=i, op=op) for i in range(1, 25)) + "    return b\n"


def test_several_rules_on_one_function_are_one_intra_method_group(tmp_path: Path):
    [(topology, lead, rules)] = _groups(tmp_path, {"m.py": _tangled("f")})
    assert (topology, lead) == (Topology.INTRA_METHOD.value, "m.f")
    assert {"cyclomatic-complexity", "npath-complexity"} <= set(rules)


def _voluminous(name: str, op: str = "+") -> str:
    """A method over the Halstead volume limit and no other: long, but straight-line."""
    return f"    def {name}(self, a, b, c):\n        return " + f" {op} ".join(f"a * b - c / {i}" for i in range(1, 60)) + "\n"


def test_one_rule_twice_in_one_class_is_no_group(tmp_path: Path):
    assert [g for g in _groups(tmp_path, {"m.py": "class A:\n" + _voluminous("f") + _voluminous("g", "-")})
            if g[0] in ("intra-class", "intra-method")] == []


def test_a_method_holding_every_finding_of_its_class_is_one_group_not_two(tmp_path: Path):
    method = "\n".join("    " + line if line else line for line in _tangled("f").replace("(a, b)", "(self, a, b)").split("\n"))
    groups = _groups(tmp_path, {"m.py": "class A:\n" + method})
    assert [(t, lead) for t, lead, _ in groups] == [("intra-method", "m.A.f")]


def test_functions_that_name_each_other_across_packages_are_one_cross_component_group(tmp_path: Path):
    groups = _groups(tmp_path, {
        "b/__init__.py": "", "b/m.py": _tangled("f"),
        "a/__init__.py": "", "a/n.py": "from b.m import f\n\n" + _tangled("g", "    f(a, b)\n", op="-"),
    })
    [(lead, rules)] = [(lead, rules) for topology, lead, rules in groups if topology == "cross-component"]
    assert lead == "m.f"                                   # named by the other, so it leads, though later by path
    assert rules.count("cyclomatic-complexity") == 2


def test_an_import_alone_does_not_relate_two_functions(tmp_path: Path):
    # n imports m but g never names f: the files are related, the anomalous code is not.
    groups = _groups(tmp_path, {
        "a/__init__.py": "", "a/m.py": _tangled("f") + "\nLIMIT = 1\n",
        "b/__init__.py": "", "b/n.py": "from a.m import LIMIT\n\n" + _tangled("g", op="-"),
    })
    assert not [g for g in groups if g[0] in ("cross-component", "intra-component")]


def test_one_rule_on_classes_of_one_tree_is_a_hierarchical_group(tmp_path: Path):
    split = "    def {a}(self):\n        return self.{a}_\n    def {b}(self):\n        return self.{b}_\n"
    groups = _groups(tmp_path, {"m.py": "class Base:\n    pass\n\n"
                                        "class A(Base):\n" + split.format(a="p", b="q") + "\n"
                                        "class B(Base):\n" + split.format(a="r", b="s") + "\n"
                                        "class Alone:\n" + split.format(a="t", b="u")})
    assert [g for g in groups if g[0] == "hierarchical"] == [("hierarchical", "m.Base", ["class-cohesion", "class-cohesion"])]


def test_lint_json_lists_groups_by_finding_id(tmp_path: Path, capsys):
    from slop import cli
    (tmp_path / "m.py").write_text(_tangled("f"))
    capsys.readouterr()
    cli.main(["lint", "--root", str(tmp_path), "--output", "json"])
    import json
    doc = json.loads(capsys.readouterr().out)
    [group] = doc["agglomerations"]
    assert group["topology"] == "intra-method" and group["lead"]["qualname"] == "m.f"
    assert set(group["findings"]) == {v["id"] for v in doc["violations"]}


def test_one_tree_holds_a_group_per_rule_each_with_its_own_id(tmp_path: Path):
    from slop.cli.lint import analyse as _analyse
    split = "    def {a}(self):\n        return self.{a}_\n    def {b}(self):\n        return self.{b}_\n"
    files = {"m.py": "class Base:\n    pass\n\nclass A(Base):\n" + split.format(a="p", b="q") +
             "\nclass B(Base):\n" + split.format(a="r", b="s"),
             "n.py": "class A:\n    pass\n\nclass B:\n    pass\n"}            # homonyms of m.A and m.B
    for name, text in files.items():
        (tmp_path / name).write_text(text, encoding="utf-8")
    analysis = _analyse(tmp_path)
    groups = [g for g in agglomerate([*analysis.report.violations, *analysis.report.warnings], analysis.corpus)
              if g.topology is Topology.HIERARCHICAL]
    assert sorted(g.rule for g in groups) == ["class-cohesion", "homonym"]
    assert len({g.id for g in groups}) == 2
