"""Carving + cyclomatic vertical slice — proves the concrete components realise
the interfaces and the aggregatable-complexity contract holds."""
from __future__ import annotations

from pathlib import Path

from slop.metrics.structural.view import Structure
from slop.scope import Callable, Class, Scope, Corpus, Module, Package, Realm
from slop.scope.identity import ScopeKind
from slop.scope import scan_corpus

SAMPLE = '''\
def f(x):
    return x

def g(x):
    if x and x > 0:
        return 1
    return 0

class Foo:
    def m(self, xs):
        for i in xs:
            if i:
                pass
'''


def _corpus(tmp_path: Path) -> Corpus:
    (tmp_path / "sample.py").write_text(SAMPLE)
    return scan_corpus(tmp_path, config=None)


def test_hierarchy_is_carved(tmp_path: Path):
    corpus = _corpus(tmp_path)
    assert isinstance(corpus, Scope) and corpus.KIND == ScopeKind.CORPUS
    (realm,) = corpus.realms()
    assert isinstance(realm, Realm) and realm.language == "python"
    (pkg,) = realm.packages()
    assert isinstance(pkg, Package)
    (mod,) = pkg.modules()
    assert isinstance(mod, Module) and mod.name == "sample"


def test_concrete_kinds_and_owners(tmp_path: Path):
    corpus = _corpus(tmp_path)
    mod = corpus.realms()[0].packages()[0].modules()[0]
    by_name = {c.name: c for c in mod.children()}
    assert isinstance(by_name["f"], Callable) and isinstance(by_name["Foo"], Class)
    foo = by_name["Foo"]
    (m,) = foo.methods()
    assert m.owner is foo and foo.owner is mod  # parented by construction


def test_cyclomatic_primitive_matches_oracle(tmp_path: Path):
    corpus = _corpus(tmp_path)
    ccn = {c.qualname: Structure.over(c).cyclomatic() for c in corpus._iter_callables()}
    assert ccn == {"sample.f": 1, "sample.g": 3, "sample.Foo.m": 3}


def test_cyclomatic_aggregates_upward(tmp_path: Path):
    corpus = _corpus(tmp_path)
    mod = corpus.realms()[0].packages()[0].modules()[0]
    foo = next(c for c in mod.children() if c.KIND == ScopeKind.CLASS)
    assert Structure.over(foo).cyclomatic() == 3        # class = sum of its methods
    assert Structure.over(mod).cyclomatic() == 7        # module = sum of f, g, Foo.m
    assert Structure.over(corpus).cyclomatic() == 7     # single module


def test_files_cardinality(tmp_path: Path):
    corpus = _corpus(tmp_path)
    mod = corpus.realms()[0].packages()[0].modules()[0]
    assert len(mod.files) == 1          # python: one file per module
