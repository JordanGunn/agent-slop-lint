"""Tests for ``Structure.imports`` — per-language tree-sitter import extraction."""
from __future__ import annotations

from pathlib import Path

from slop.tree.tree import Tree


def _imports_for(tmp_path: Path, files: dict[str, str]):
    for name, content in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    t = Tree(tmp_path)
    t.scan()
    return t.structure.imports()


class TestPython:
    def test_import_statement(self, tmp_path: Path):
        imps = _imports_for(tmp_path, {"a.py": "import os\nimport sys\n"})
        modules = sorted((i.module, i.kind) for i in imps)
        assert modules == [("os", "import"), ("sys", "import")]

    def test_from_import(self, tmp_path: Path):
        imps = _imports_for(tmp_path, {
            "a.py": "from collections import OrderedDict\nfrom slop.tree import Tree\n",
        })
        modules = sorted((i.module, i.kind) for i in imps)
        assert modules == [
            ("collections", "from_import"),
            ("slop.tree", "from_import"),
        ]

    def test_aliased_import(self, tmp_path: Path):
        imps = _imports_for(tmp_path, {"a.py": "import numpy as np\n"})
        assert [(i.module, i.kind) for i in imps] == [("numpy", "import")]


class TestJavaScript:
    def test_esm(self, tmp_path: Path):
        imps = _imports_for(tmp_path, {
            "a.js": "import {x} from './util';\nimport y from 'pkg';\n",
        })
        modules = sorted((i.module, i.kind) for i in imps)
        assert modules == [("./util", "esm"), ("pkg", "esm")]

    def test_require(self, tmp_path: Path):
        imps = _imports_for(tmp_path, {
            "a.js": "const fs = require('fs');\nconst {x} = require('./util');\n",
        })
        modules = sorted((i.module, i.kind) for i in imps)
        assert modules == [("./util", "require"), ("fs", "require")]


class TestTypeScript:
    def test_esm(self, tmp_path: Path):
        imps = _imports_for(tmp_path, {
            "a.ts": "import {x} from './util';\nimport type {Y} from 'pkg';\n",
        })
        modules = sorted((i.module, i.kind) for i in imps if i.kind == "esm")
        assert modules == [("./util", "esm"), ("pkg", "esm")]


class TestGo:
    def test_single_import(self, tmp_path: Path):
        imps = _imports_for(tmp_path, {
            "a.go": 'package a\nimport "fmt"\n',
        })
        assert [(i.module, i.kind) for i in imps] == [("fmt", "go_import")]

    def test_block_import(self, tmp_path: Path):
        imps = _imports_for(tmp_path, {
            "a.go": 'package a\nimport (\n\t"fmt"\n\t"strings"\n)\n',
        })
        modules = sorted((i.module, i.kind) for i in imps)
        assert modules == [("fmt", "go_import"), ("strings", "go_import")]


class TestJava:
    def test_import_declaration(self, tmp_path: Path):
        imps = _imports_for(tmp_path, {
            "A.java": (
                "package com.example;\n"
                "import java.util.List;\n"
                "import java.util.Map;\n"
                "class A {}\n"
            ),
        })
        modules = sorted((i.module, i.kind) for i in imps)
        assert modules == [
            ("java.util.List", "java_import"),
            ("java.util.Map", "java_import"),
        ]


class TestCSharp:
    def test_using(self, tmp_path: Path):
        imps = _imports_for(tmp_path, {
            "A.cs": (
                "using System;\n"
                "using System.Collections.Generic;\n"
                "class A {}\n"
            ),
        })
        modules = sorted((i.module, i.kind) for i in imps)
        assert modules == [
            ("System", "csharp_using"),
            ("System.Collections.Generic", "csharp_using"),
        ]


class TestRust:
    def test_use(self, tmp_path: Path):
        imps = _imports_for(tmp_path, {
            "a.rs": (
                "use std::collections::HashMap;\n"
                "use serde;\n"
                "fn main() {}\n"
            ),
        })
        kinds = {i.kind for i in imps}
        assert kinds == {"use"}
        modules = sorted(i.module for i in imps)
        # Rust's scoped_identifier capture matches the full path;
        # the bare-identifier branch handles ``use serde;``.
        assert "std::collections::HashMap" in modules
        assert "serde" in modules


class TestC:
    def test_include_local_and_system(self, tmp_path: Path):
        imps = _imports_for(tmp_path, {
            "a.c": (
                '#include "foo.h"\n'
                "#include <stdio.h>\n"
                "int main(void) { return 0; }\n"
            ),
        })
        records = sorted((i.module, i.kind) for i in imps)
        # The walker strips ``"`` and ``<>`` from the captured text.
        assert records == [
            ("foo.h", "include_local"),
            ("stdio.h", "include_system"),
        ]


class TestRuby:
    def test_require(self, tmp_path: Path):
        imps = _imports_for(tmp_path, {
            "a.rb": (
                "require 'json'\n"
                "require_relative './helper'\n"
                "load 'config.rb'\n"
            ),
        })
        modules = sorted(i.module for i in imps)
        assert modules == ["./helper", "config.rb", "json"]
        # All three share the same kind label — discrimination happens
        # via the method captured separately at the kernel layer; for
        # this view, ``ruby_require`` is the umbrella kind.
        assert {i.kind for i in imps} == {"ruby_require"}


class TestJulia:
    def test_using_and_import(self, tmp_path: Path):
        imps = _imports_for(tmp_path, {
            "a.jl": (
                "using Foo\n"
                "using Bar.Baz\n"
                "import Qux\n"
            ),
        })
        modules = sorted((i.module, i.kind) for i in imps)
        # Bar.Baz is captured as scoped_identifier, emitted as the full
        # ``Bar.Baz`` text.
        assert ("Foo", "julia_using") in modules
        assert ("Qux", "julia_import") in modules
        assert any(m == "Bar.Baz" for m, _ in modules)


class TestEmptyAndNoQueries:
    def test_no_imports(self, tmp_path: Path):
        imps = _imports_for(tmp_path, {"a.py": "x = 1\n"})
        assert imps == []
