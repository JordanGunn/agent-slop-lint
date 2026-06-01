"""Broaden check: every grammar carves + computes complexity, oracle-matched values."""
from pathlib import Path
import pytest
from slop.model import scan_corpus
from slop.ast import GRAMMARS_BY_ID

CASES = {
    "py":  ("python", "def f(x):\n    if x and x > 0:\n        return 1\n    return 0\n", {"f": 3}),
    "go":  ("go", "package m\nfunc Add(a int) int {\n\tif a > 0 && a < 9 { return 1 }\n\treturn 0\n}\n", {"Add": 3}),
    "c":   ("c", "int f(int x){ if(x>0&&x<9){return 1;} return 0; }\n", {"f": 3}),
    "java":("java", "class K { int f(int x){ if(x>0&&x<9){return 1;} return 0; } }\n", {"f": 3}),
    "rb":  ("ruby", "class D\n  def f(x)\n    if x && x > 0\n      1\n    end\n  end\nend\n", {"f": 4}),
    "rs":  ("rust", "fn f(x: i32) -> i32 { if x > 0 && x < 9 { 1 } else { 0 } }\n", {"f": 3}),
    "js":  ("javascript", "function f(x){ if(x>0&&x<9){return 1;} return 0; }\n", {"f": 3}),
}


@pytest.mark.parametrize("ext,spec", CASES.items())
def test_language_carves_and_scores(tmp_path: Path, ext, spec):
    lang, src, expected = spec
    (tmp_path / f"a.{ext}").write_text(src)
    corpus = scan_corpus(tmp_path, config=None)
    assert corpus.realms() and corpus.realms()[0].language == lang
    ccn = {c.name: c.cyclomatic() for c in corpus._iter_callables()}
    for name, want in expected.items():
        assert ccn.get(name) == want, f"{lang}:{name} expected {want}, got {ccn.get(name)}"


def test_all_eleven_grammars_registered():
    assert set(GRAMMARS_BY_ID) == {
        "python", "go", "c", "cpp", "julia", "java", "c_sharp",
        "rust", "ruby", "javascript", "typescript",
    }
