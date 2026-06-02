from pathlib import Path
from slop.metrics.structural.view import Structure
from slop.scope import scan_corpus

def test_orphans(tmp_path: Path):
    (tmp_path / "a.py").write_text(
        "def used_helper():\n    return 1\n\ndef unreferenced_function():\n    return 2\n\nclass UnusedWidget:\n    pass\n"
    )
    (tmp_path / "b.py").write_text("from a import used_helper\n\ndef main():\n    return used_helper()\n")
    orphs = {o.qualname for o in Structure.over(scan_corpus(tmp_path, config=None)).orphans()}
    assert "a.used_helper" not in orphs        # referenced in b.py
    assert "a.unreferenced_function" in orphs
    assert "a.UnusedWidget" in orphs

def test_is_runt(tmp_path: Path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("")  # trivial, empty
    pkg = scan_corpus(tmp_path, config=None).realms()[0].packages()[0]
    assert Structure.over(pkg).is_runt() is True

def test_hotspots_non_git_is_empty(tmp_path: Path):
    (tmp_path / "a.py").write_text("def f():\n    return 1\n")
    assert Structure.over(scan_corpus(tmp_path, config=None)).hotspots() == []
