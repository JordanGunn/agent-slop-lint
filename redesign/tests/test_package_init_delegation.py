"""Package-init module naming is delegated to grammar.package_init_name(), not a
hardcoded "__init__.py" literal in scope/carve or graph.build (language-agnosticism
#40).

A package-init module is importable by its directory path (Python ``import core``
resolves ``core/__init__.py``), so graph.build gives it the parent-package name
spellings. That branch must fire only for a grammar that *has* an init-file
convention; for a language with none (init_name=None, e.g. Go/Rust) a file that
happens to be named like an init file gets no special treatment.
"""
from __future__ import annotations

from pathlib import Path

from slop.ast.grammar import GRAMMARS_BY_ID
from slop.graph.build import _module_names_for_path


def test_init_spellings_only_when_init_name_matches():
    p = Path("proj/core/__init__.py")
    with_py = _module_names_for_path(p, "__init__.py")
    # Python: package-init is also importable by its directory path.
    assert "core" in with_py and "proj.core" in with_py
    # No init-file convention: no parent-package spellings (the hardcode would have
    # fired on the literal filename regardless of language).
    without = _module_names_for_path(p, None)
    assert "core" not in without and "proj.core" not in without


def test_package_init_name_is_python_only():
    assert GRAMMARS_BY_ID["python"].package_init_name() == "__init__.py"
    for gid, grammar in GRAMMARS_BY_ID.items():
        if gid == "python":
            continue
        assert grammar.package_init_name() is None, gid
