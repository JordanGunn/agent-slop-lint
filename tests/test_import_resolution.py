"""Import resolution: a relative import names one place, anchored at the importing file.

Each corpus holds a same-named module earlier in path order than the real target, which is the
module a bare-name lookup would pick."""
from __future__ import annotations

from pathlib import Path

from slop.identity import relative_path
from slop.scope import scan_corpus


def _edges(root: Path, files: dict[str, str]) -> set[tuple[str, str]]:
    for name, text in files.items():
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_text(text, encoding="utf-8")
    graph = scan_corpus(root, config=None).context.dep_graph

    return {(relative_path(e.from_, root), relative_path(e.to, root)) for e in graph.edges() if e.resolved}


def test_python_relative_import_is_anchored_at_the_importing_package(tmp_path: Path):
    edges = _edges(tmp_path, {"p/__init__.py": "", "p/cli/__init__.py": "", "p/cli/find.py": "x = 1\n",
                              "p/scope/__init__.py": "", "p/scope/find.py": "def walk(): pass\n",
                              "p/rules/__init__.py": "", "p/rules/r.py": "from ..scope.find import walk\n"})
    assert ("p/rules/r.py", "p/scope/find.py") in edges
    assert ("p/rules/r.py", "p/cli/find.py") not in edges


def test_python_from_package_import_depends_on_submodules_and_on_the_package_only_for_attributes(tmp_path: Path):
    edges = _edges(tmp_path, {"p/__init__.py": "from . import a, b, own\nfrom .q import thing\nown = 1\n",
                              "p/a.py": "", "p/b.py": "", "p/q/__init__.py": "thing = 1\n",
                              "p/c.py": "from . import a\n"})
    assert {("p/__init__.py", "p/a.py"), ("p/__init__.py", "p/b.py"), ("p/__init__.py", "p/q/__init__.py")} <= edges
    assert ("p/c.py", "p/a.py") in edges
    assert ("p/c.py", "p/__init__.py") not in edges          # takes a submodule, nothing from the package
    assert ("p/__init__.py", "p/__init__.py") not in edges   # `own` is its own attribute: no self-edge


def test_a_package_importing_its_submodule_that_imports_a_sibling_is_not_a_cycle(tmp_path: Path):
    _edges(tmp_path, {"p/__init__.py": "from .carve import scan\n",
                      "p/carve.py": "from . import parts\ndef scan(): pass\n", "p/parts.py": ""})
    assert scan_corpus(tmp_path, config=None).context.dep_graph.cycles() == []


def test_python_absolute_import_never_resolves_by_its_last_segment(tmp_path: Path):
    assert _edges(tmp_path, {"a/path.py": "", "b.py": "from os.path import join\n"}) == set()
    assert _edges(tmp_path, {"c.py": "import a.path\n"}) >= {("c.py", "a/path.py")}


def test_ecmascript_relative_specifiers_name_a_file_beside_the_importer(tmp_path: Path):
    edges = _edges(tmp_path, {"a/util.js": "", "b/util.js": "", "b/lib/index.js": "", "b/model.ts": "",
                              "b/main.js": 'import u from "./util";\nimport v from "../a/util.js";\n'
                                           'const w = require("./lib");\nimport m from "./model.js";\n'})
    assert edges == {("b/main.js", "b/util.js"), ("b/main.js", "a/util.js"), ("b/main.js", "b/lib/index.js"),
                     ("b/main.js", "b/model.ts")}                       # ./model.js written for model.ts


def test_c_quoted_include_looks_beside_the_including_file(tmp_path: Path):
    edges = _edges(tmp_path, {"a/x.h": "int a;\n", "b/x.h": "int b;\n", "b/main.c": '#include "x.h"\n'})
    assert edges == {("b/main.c", "b/x.h")}


def test_ruby_require_relative_names_a_file_beside_the_requiring_one(tmp_path: Path):
    edges = _edges(tmp_path, {"a/util.rb": "", "b/util.rb": "", "b/main.rb": 'require_relative "util"\n'})
    assert edges == {("b/main.rb", "b/util.rb")}


def test_rust_self_super_and_crate_paths_walk_the_module_tree(tmp_path: Path):
    edges = _edges(tmp_path, {
        "src/lib.rs": "mod net;\nmod fs;\n", "src/fs.rs": "use crate::net::udp::Socket;\npub struct File;\n",
        "src/a/udp.rs": "pub struct Socket;\n",                       # same name, wrong place
        "src/net/mod.rs": "pub mod tcp;\npub mod udp;\n", "src/net/udp.rs": "pub struct Socket;\n",
        "src/net/tcp/inner.rs": "pub struct Buf;\n",
        "src/net/tcp.rs": "use super::udp::Socket;\nuse crate::fs::File;\nuse self::inner::Buf;\nuse super::Thing;\n",
    })
    tcp = {to for frm, to in edges if frm == "src/net/tcp.rs"}
    assert tcp == {"src/net/udp.rs", "src/fs.rs", "src/net/tcp/inner.rs", "src/net/mod.rs"}
    assert {to for frm, to in edges if frm == "src/fs.rs"} == {"src/net/udp.rs"}   # the deepest module named
