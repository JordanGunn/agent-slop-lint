"""Each scope accessor returns only the children of its own kind."""
from __future__ import annotations

from pathlib import Path

from slop.scope import scan_corpus
from slop.scope.identity import ScopeKind


def _find(root, kind: ScopeKind, name: str):
    stack = [root]
    while stack:
        n = stack.pop()
        if n.id.kind is kind and n.name == name:
            return n
        stack.extend(n.children())
    raise LookupError(name)


def test_accessors_return_only_their_own_kind(tmp_path: Path):
    (tmp_path / "top").mkdir()
    (tmp_path / "top" / "sub").mkdir()
    (tmp_path / "top" / "sub" / "__init__.py").write_text("")
    (tmp_path / "top" / "__init__.py").write_text("")
    (tmp_path / "top" / "m.py").write_text(
        "class K:\n    class Inner:\n        pass\n    def method(self):\n        def local():\n            return 1\n        return local\n")
    corpus = scan_corpus(tmp_path, config=None)

    package = _find(corpus, ScopeKind.PACKAGE, "top")
    assert {m.name for m in package.modules()} == {"top", "m"}      # `top` is the package's own __init__.py
    assert all(m.KIND is ScopeKind.MODULE for m in package.modules())
    realm = corpus.realms()[0]
    assert {p.name for p in realm.packages()} == {"top", "top/sub"}       # siblings, not nested
    assert all(p.KIND is ScopeKind.PACKAGE for p in realm.packages())

    klass = _find(corpus, ScopeKind.CLASS, "K")
    assert [c.name for c in klass.methods()] == ["method"]

    method = _find(corpus, ScopeKind.CALLABLE, "method")
    assert [c.name for c in method.nested()] == ["local"]

    assert [r.language for r in corpus.realms()] == ["python"]
    assert all(r.KIND is ScopeKind.REALM for r in corpus.realms())
