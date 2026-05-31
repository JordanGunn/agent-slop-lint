from pathlib import Path
from slop.model import scan_corpus

def test_escape_hatch_density(tmp_path: Path):
    (tmp_path / "a.py").write_text(
        "from typing import Any\n\ndef f(x: int, y: Any) -> str:\n    z: Any = 1\n    return ''\n"
    )
    mod = scan_corpus(tmp_path, config=None).realms()[0].packages()[0].modules()[0]
    assert mod.escape_hatch_density() == 0.5  # x:int, y:Any, ->str, z:Any => 2/4

def test_definition_count(tmp_path: Path):
    (tmp_path / "a.py").write_text("def f(): pass\ndef g(): pass\nclass C: pass\n")
    mod = scan_corpus(tmp_path, config=None).realms()[0].packages()[0].modules()[0]
    assert mod.definition_count() == 3
