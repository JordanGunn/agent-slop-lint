from pathlib import Path
from slop.metrics.structural.view import Structure
from slop.scope import scan_corpus

def test_definition_count(tmp_path: Path):
    (tmp_path / "a.py").write_text("def f(): pass\ndef g(): pass\nclass C: pass\n")
    mod = scan_corpus(tmp_path, config=None).realms()[0].packages()[0].modules()[0]
    assert Structure.over(mod).definition_count() == 3
