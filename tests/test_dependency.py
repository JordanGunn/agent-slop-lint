from pathlib import Path
from slop.metrics.structural.view import Structure
from slop.scope import scan_corpus


def test_cycle_detected(tmp_path: Path):
    (tmp_path / "a.py").write_text("import b\n")
    (tmp_path / "b.py").write_text("import a\n")
    cyc = Structure.over(scan_corpus(tmp_path, config=None)).dependency_cycles()
    assert len(cyc) == 1
    assert sorted(cyc[0].members) == ["a.py", "b.py"]       # root-relative path labels
    assert len({s.spans[0].path for s in cyc[0].scopes}) == 2


def test_same_named_modules_in_two_packages_are_two_cycle_members(tmp_path: Path):
    # `a/x.py` and `b/x.py` are both the module `x`; a cycle between them used to read
    # "x -> x" and collapse to one module.
    for pkg, other in (("a", "b"), ("b", "a")):
        (tmp_path / pkg).mkdir()
        (tmp_path / pkg / "__init__.py").write_text("")
        (tmp_path / pkg / "x.py").write_text(f"from {other}.x import f\n")
    cyc = Structure.over(scan_corpus(tmp_path, config=None)).dependency_cycles()
    assert [c.members for c in cyc] == [("a/x.py", "b/x.py")]
    assert len(set(cyc[0].scopes)) == 2


def test_no_cycle(tmp_path: Path):
    (tmp_path / "a.py").write_text("import b\n")
    (tmp_path / "b.py").write_text("x = 1\n")
    assert Structure.over(scan_corpus(tmp_path, config=None)).dependency_cycles() == []


def test_dependency_edges_resolve(tmp_path: Path):
    (tmp_path / "a.py").write_text("import b\n")
    (tmp_path / "b.py").write_text("x = 1\n")
    g = scan_corpus(tmp_path, config=None).context.dep_graph
    resolved = [e for e in g.edges() if e.resolved]
    assert len(resolved) == 1 and resolved[0].raw_specifier == "b"


def test_martin_abstractness(tmp_path: Path):
    (tmp_path / "m.py").write_text(
        "from abc import ABC\nclass Base(ABC):\n    pass\nclass Impl:\n    pass\n"
    )
    pkg = scan_corpus(tmp_path, config=None).realms()[0].packages()[0]
    mm = Structure.over(pkg).martin_metrics()
    assert mm.abstractness == 0.5     # 1 abstract / 2 classes
    assert mm.afferent == 0 and mm.efferent == 0
    assert Structure.over(pkg).in_zone_of_pain() is False   # undefined coupling -> not classifiable
