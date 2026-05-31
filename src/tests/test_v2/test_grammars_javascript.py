"""Characterization tests for the JavaScript/TypeScript grammar navigation.

javascript.py had no dedicated test file; its parameter extractors and the
mutation walker were exercised only indirectly through the rule tests. These
lock current behavior before the navigation-helper extraction:

- JS hidden_mutators (require_type_annotation=False): collection-method
  mutations through parameters, default params, the require=True skip, and the
  arrow-bare-param non-detection (the single identifier sits in the
  ``parameter`` field, so the arrow fallback never fires).
- TS hidden_mutators (require_type_annotation=True): collection-typed params
  via type-annotation token matching; plain/unannotated params skipped.
"""
from __future__ import annotations

from pathlib import Path

from slop.tree.parse import parse_file
from slop.language.grammars import JavaScript, TypeScript

_CALLABLE = (
    "function_declaration", "arrow_function",
    "method_definition", "function_expression",
)


def _first_callable(tree):
    stack = [tree.root_node]
    while stack:
        n = stack.pop()
        if n.type in _CALLABLE:
            return n
        stack.extend(n.children)
    raise AssertionError("no callable node found")


def _run(tmp_path: Path, lang: str, ext: str, grammar, src: str, **kw):
    p = tmp_path / f"x.{ext}"
    p.write_text(src)
    parsed = parse_file(p, lang)
    assert parsed is not None
    tree, content = parsed
    return grammar.hidden_mutators(_first_callable(tree), content, **kw)


class TestJsHiddenMutators:
    def test_array_push(self, tmp_path: Path):
        out = _run(tmp_path, "javascript", "js", JavaScript, "function f(arr){ arr.push(1); }\n", require_type_annotation=False)
        assert out == [("arr", "push", 1)]

    def test_map_set(self, tmp_path: Path):
        out = _run(tmp_path, "javascript", "js", JavaScript, "function f(m){ m.set('k',1); }\n", require_type_annotation=False)
        assert out == [("m", "set", 1)]

    def test_non_mutating_method_ignored(self, tmp_path: Path):
        out = _run(tmp_path, "javascript", "js", JavaScript, "function f(arr){ arr.map(x=>x); }\n", require_type_annotation=False)
        assert out == []

    def test_default_param(self, tmp_path: Path):
        out = _run(tmp_path, "javascript", "js", JavaScript, "function f(arr=[]){ arr.push(1); }\n", require_type_annotation=False)
        assert out == [("arr", "push", 1)]

    def test_arrow_bare_param_not_detected(self, tmp_path: Path):
        # Current behavior: bare arrow param sits in the `parameter` field,
        # so the arrow-fallback (which only runs when params_node is None)
        # never fires.
        out = _run(tmp_path, "javascript", "js", JavaScript, "const f = arr => { arr.push(1); };\n", require_type_annotation=False)
        assert out == []

    def test_require_annotation_true_skips(self, tmp_path: Path):
        out = _run(tmp_path, "javascript", "js", JavaScript, "function f(arr){ arr.push(1); }\n", require_type_annotation=True)
        assert out == []


class TestTsHiddenMutators:
    def test_array_annotation(self, tmp_path: Path):
        out = _run(tmp_path, "typescript", "ts", TypeScript, "function f(arr: Array<number>){ arr.push(1); }\n", require_type_annotation=True)
        assert out == [("arr", "push", 1)]

    def test_set_annotation(self, tmp_path: Path):
        out = _run(tmp_path, "typescript", "ts", TypeScript, "function f(s: Set<string>){ s.add('x'); }\n", require_type_annotation=True)
        assert out == [("s", "add", 1)]

    def test_plain_type_skipped(self, tmp_path: Path):
        out = _run(tmp_path, "typescript", "ts", TypeScript, "function f(n: number){ n.toString(); }\n", require_type_annotation=True)
        assert out == []

    def test_unannotated_skipped(self, tmp_path: Path):
        out = _run(tmp_path, "typescript", "ts", TypeScript, "function f(arr){ arr.push(1); }\n", require_type_annotation=True)
        assert out == []
