"""Tests for ``Structure.dependency_graph`` — resolved file→file edges."""
from __future__ import annotations

from pathlib import Path

from slop.tree.tree import Tree


def _graph_for(tmp_path: Path, files: dict[str, str]):
    for name, content in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    t = Tree(tmp_path)
    t.scan()
    return t.structure.dependency_graph(), t


def _key(tmp_path: Path, name: str) -> str:
    # ``Tree`` returns parses keyed by the path it was constructed with;
    # when constructed from a tmp_path it stores absolute paths.
    return str(tmp_path / name)


class TestPythonResolution:
    def test_intra_package_resolves(self, tmp_path: Path):
        graph, _ = _graph_for(tmp_path, {
            "pkg/__init__.py": "",
            "pkg/a.py": "from pkg import b\n",
            "pkg/b.py": "VALUE = 1\n",
        })
        a_imports = graph.efferent[_key(tmp_path, "pkg/a.py")]
        # ``from pkg import b`` resolves to the ``__init__.py``.
        assert _key(tmp_path, "pkg/__init__.py") in a_imports

    def test_relative_path_form(self, tmp_path: Path):
        graph, _ = _graph_for(tmp_path, {
            "pkg/__init__.py": "",
            "pkg/a.py": "from pkg.b import VALUE\n",
            "pkg/b.py": "VALUE = 1\n",
        })
        a_imports = graph.efferent[_key(tmp_path, "pkg/a.py")]
        assert _key(tmp_path, "pkg/b.py") in a_imports

    def test_external_modules_dropped(self, tmp_path: Path):
        graph, _ = _graph_for(tmp_path, {
            "a.py": "import os\nimport collections\n",
            "b.py": "VALUE = 1\n",
        })
        # ``os`` and ``collections`` aren't in the corpus; only the
        # in-corpus edges (none in this case) survive resolution.
        a_imports = graph.efferent[_key(tmp_path, "a.py")]
        assert a_imports == frozenset()


class TestReverseAdjacency:
    def test_afferent_reverses_efferent(self, tmp_path: Path):
        graph, _ = _graph_for(tmp_path, {
            "a.py": "from b import VALUE\n",
            "b.py": "VALUE = 1\n",
        })
        a = _key(tmp_path, "a.py")
        b = _key(tmp_path, "b.py")
        assert b in graph.efferent[a]
        assert a in graph.afferent[b]


class TestSelfEdges:
    def test_self_imports_dropped(self, tmp_path: Path):
        # Synthetic: a file ``b.py`` whose stem-match would resolve to
        # itself. The resolver rejects self-edges.
        graph, _ = _graph_for(tmp_path, {
            "b.py": "import b\n",  # NB: imports its own stem
        })
        b = _key(tmp_path, "b.py")
        assert b not in graph.efferent[b]


class TestGoResolution:
    def test_intra_module_resolves(self, tmp_path: Path):
        graph, _ = _graph_for(tmp_path, {
            "main.go": (
                'package main\n'
                'import "example.com/p/util"\n'
                'func main() {}\n'
            ),
            "util/util.go": "package util\n",
        })
        main = _key(tmp_path, "main.go")
        util = _key(tmp_path, "util/util.go")
        # The default resolver matches the trailing segment ``util`` against
        # the file's stem (also ``util``).
        assert util in graph.efferent[main]


class TestCycles:
    def test_no_cycles_when_acyclic(self, tmp_path: Path):
        graph, t = _graph_for(tmp_path, {
            "a.py": "from b import x\n",
            "b.py": "x = 1\n",
        })
        assert t.structure.dependency_cycles() == []

    def test_two_node_cycle(self, tmp_path: Path):
        graph, t = _graph_for(tmp_path, {
            "a.py": "from b import x\n",
            "b.py": "from a import x\n",
        })
        cycles = t.structure.dependency_cycles()
        assert len(cycles) == 1
        assert {Path(p).name for p in cycles[0]} == {"a.py", "b.py"}

    def test_strongly_connected_three_node_cycle_collapses_to_one(self, tmp_path: Path):
        graph, t = _graph_for(tmp_path, {
            "a.py": "import b\n",
            "b.py": "import c\n",
            "c.py": "import a\n",
        })
        cycles = t.structure.dependency_cycles()
        assert len(cycles) == 1
        assert {Path(p).name for p in cycles[0]} == {"a.py", "b.py", "c.py"}


class TestCResolution:
    def test_local_include_resolves_to_header(self, tmp_path: Path):
        graph, _ = _graph_for(tmp_path, {
            "main.c": '#include "foo.h"\nint main(void) { return 0; }\n',
            "foo.h": "int foo(void);\n",
        })
        main = _key(tmp_path, "main.c")
        header = _key(tmp_path, "foo.h")
        assert header in graph.efferent[main]
