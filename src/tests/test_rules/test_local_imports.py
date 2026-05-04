"""Tests for structural.local_imports rule."""

from __future__ import annotations

from pathlib import Path

import pytest

from slop._structural.local_imports import local_imports_kernel
from slop.models import RuleConfig, SlopConfig
from slop.rules.local_imports import run_local_imports


# ---------------------------------------------------------------------------
# Kernel – Python (AST tier)
# ---------------------------------------------------------------------------


def test_kernel_clean_when_module_level_only(tmp_path: Path):
    (tmp_path / "a.py").write_text("import os\nimport sys\n\ndef f():\n    pass\n")
    result = local_imports_kernel(tmp_path)
    assert result.local_imports == []
    assert result.errors == []


def test_kernel_detects_import_inside_function(tmp_path: Path):
    (tmp_path / "a.py").write_text(
        "def my_func():\n"
        "    import os\n"
        "    return os.getcwd()\n"
    )
    result = local_imports_kernel(tmp_path)
    assert len(result.local_imports) == 1
    li = result.local_imports[0]
    assert li.language == "python"
    assert li.function == "my_func"
    assert li.line == 2
    assert "import os" in li.module


def test_kernel_detects_from_import_inside_function(tmp_path: Path):
    (tmp_path / "a.py").write_text(
        "def loader():\n"
        "    from pathlib import Path\n"
        "    return Path('.')\n"
    )
    result = local_imports_kernel(tmp_path)
    assert len(result.local_imports) == 1
    assert "pathlib" in result.local_imports[0].module


def test_kernel_detects_multiple_local_imports(tmp_path: Path):
    (tmp_path / "a.py").write_text(
        "def do_stuff():\n"
        "    import os\n"
        "    import sys\n"
        "    return os.getcwd(), sys.version\n"
    )
    result = local_imports_kernel(tmp_path)
    assert len(result.local_imports) == 2
    funcs = {li.function for li in result.local_imports}
    assert funcs == {"do_stuff"}


def test_kernel_detects_nested_function_import(tmp_path: Path):
    (tmp_path / "a.py").write_text(
        "def outer():\n"
        "    def inner():\n"
        "        import json\n"
        "    inner()\n"
    )
    result = local_imports_kernel(tmp_path)
    # import is inside inner(); that is the nearest enclosing function
    assert len(result.local_imports) == 1
    assert result.local_imports[0].function == "inner"


def test_kernel_ignores_non_python_files(tmp_path: Path):
    (tmp_path / "data.txt").write_text("import something\n")
    result = local_imports_kernel(tmp_path)
    assert result.local_imports == []


def test_kernel_multiple_files(tmp_path: Path):
    (tmp_path / "clean.py").write_text("import os\n\ndef f():\n    pass\n")
    (tmp_path / "dirty.py").write_text("def g():\n    import os\n")
    result = local_imports_kernel(tmp_path)
    assert len(result.local_imports) == 1
    assert result.local_imports[0].file.endswith("dirty.py")


# ---------------------------------------------------------------------------
# Kernel – Rust (text tier)
# ---------------------------------------------------------------------------


def test_kernel_rust_detects_indented_use(tmp_path: Path):
    (tmp_path / "lib.rs").write_text(
        "fn process() {\n"
        "    use std::collections::HashMap;\n"
        "    let m = HashMap::new();\n"
        "}\n"
    )
    result = local_imports_kernel(tmp_path)
    assert len(result.local_imports) == 1
    li = result.local_imports[0]
    assert li.language == "rust"
    assert li.function == "process"


def test_kernel_rust_ignores_top_level_use(tmp_path: Path):
    (tmp_path / "lib.rs").write_text("use std::collections::HashMap;\n\nfn f() {}\n")
    result = local_imports_kernel(tmp_path)
    assert result.local_imports == []


# ---------------------------------------------------------------------------
# Rule wrapper
# ---------------------------------------------------------------------------


def test_rule_pass_when_no_local_imports(tmp_path: Path):
    (tmp_path / "a.py").write_text("import os\n\ndef f():\n    return os.getcwd()\n")
    rc = RuleConfig(enabled=True, severity="warning", params={"threshold": 0})
    result = run_local_imports(tmp_path, rc, SlopConfig(root=str(tmp_path)))
    assert result.status == "pass"
    assert result.violations == []


def test_rule_fail_on_local_import(tmp_path: Path):
    (tmp_path / "a.py").write_text("def f():\n    import os\n    return os.getcwd()\n")
    rc = RuleConfig(enabled=True, severity="warning", params={"threshold": 0})
    result = run_local_imports(tmp_path, rc, SlopConfig(root=str(tmp_path)))
    assert result.status == "fail"
    assert len(result.violations) == 1
    v = result.violations[0]
    assert v.rule == "structural.local_imports"
    assert v.severity == "warning"
    assert "import" in v.message.lower()


def test_rule_threshold_suppresses_violations(tmp_path: Path):
    # One local import but threshold=1 → should pass
    (tmp_path / "a.py").write_text("def f():\n    import os\n    return os.getcwd()\n")
    rc = RuleConfig(enabled=True, severity="warning", params={"threshold": 1})
    result = run_local_imports(tmp_path, rc, SlopConfig(root=str(tmp_path)))
    assert result.status == "pass"


def test_rule_summary_counts(tmp_path: Path):
    (tmp_path / "a.py").write_text(
        "def f():\n    import os\n    import sys\n    return os.getcwd()\n"
    )
    rc = RuleConfig(enabled=True, severity="warning", params={"threshold": 0})
    result = run_local_imports(tmp_path, rc, SlopConfig(root=str(tmp_path)))
    assert result.summary["local_imports_found"] == 2
    assert result.summary["violation_count"] == 2
