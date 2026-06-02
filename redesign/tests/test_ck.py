from pathlib import Path
from slop.metrics.structural.view import Structure
from slop.scope import scan_corpus

SRC = '''\
class Base:
    pass

class Mid(Base):
    pass

class Leaf(Mid):
    def m(self):
        x = Base()
        return x
'''

def _classes(tmp_path: Path) -> dict:
    (tmp_path / "ck.py").write_text(SRC)
    mod = scan_corpus(tmp_path, config=None).realms()[0].packages()[0].modules()[0]
    return {c.name: c for c in mod.children() if c.KIND.name == "CLASS"}

def test_dit(tmp_path: Path):
    cs = _classes(tmp_path)
    assert (Structure.over(cs["Base"]).dit(), Structure.over(cs["Mid"]).dit(), Structure.over(cs["Leaf"]).dit()) == (0, 1, 2)

def test_noc(tmp_path: Path):
    cs = _classes(tmp_path)
    assert (Structure.over(cs["Base"]).noc(), Structure.over(cs["Mid"]).noc(), Structure.over(cs["Leaf"]).noc()) == (1, 1, 0)

def test_cbo(tmp_path: Path):
    cs = _classes(tmp_path)
    assert (Structure.over(cs["Base"]).cbo(), Structure.over(cs["Mid"]).cbo(), Structure.over(cs["Leaf"]).cbo()) == (0, 1, 2)

def test_ck_record(tmp_path: Path):
    cs = _classes(tmp_path)
    ck = Structure.over(cs["Leaf"]).ck()
    assert (ck.dit, ck.noc, ck.cbo, ck.nom, ck.lcom) == (2, 0, 2, 1, None)
