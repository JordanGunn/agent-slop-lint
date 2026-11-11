"""Import directions inside slop.infer: contract at the bottom, nothing imports upward.

The table is the architecture of the package. ``tests/test_layers.py`` covers imports from
outside ``infer``; this covers the subpackages among themselves.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

INFER = Path(__file__).resolve().parent.parent / "src" / "slop" / "infer"

#: subpackage -> the only sibling subpackages it may import.
ALLOWED: dict[str, set[str]] = {
    "bundle": set(),
    "contract": set(),
    "ledger": {"contract"},
    "frame": {"bundle", "contract"},
    "source": {"contract", "frame"},
    "apply": {"contract", "frame", "ledger", "source"},
}


def infer_siblings(source: str, module: str, *, is_package: bool) -> list[tuple[int, str]]:
    """``(line, subpackage)`` for each import of ``slop.infer.<subpackage>`` in ``source``."""
    parts = module.split(".")
    base_of_file = parts if is_package else parts[:-1]
    found: list[tuple[int, str]] = []
    for node in ast.walk(ast.parse(source)):
        targets: list[list[str]] = []
        if isinstance(node, ast.ImportFrom):
            base = base_of_file[: len(base_of_file) - (node.level - 1)] if node.level else []
            if node.module:
                targets.append(base + node.module.split("."))
            else:
                targets.extend(base + [alias.name] for alias in node.names)
        elif isinstance(node, ast.Import):
            targets.extend(alias.name.split(".") for alias in node.names)
        for segs in targets:
            if len(segs) > 2 and segs[:2] == ["slop", "infer"]:
                found.append((node.lineno, segs[2]))
    return found


def _imports_of(subpackage: str) -> list[tuple[str, int, str]]:
    out = []
    for path in sorted((INFER / subpackage).rglob("*.py")):
        rel = path.relative_to(INFER.parent.parent)
        module = ".".join(rel.with_suffix("").parts)
        is_package = path.name == "__init__.py"
        if is_package:
            module = module.removesuffix(".__init__")
        for line, target in infer_siblings(path.read_text(), module, is_package=is_package):
            if target != subpackage:
                out.append((str(rel), line, target))
    return out


@pytest.mark.parametrize("subpackage,allowed", sorted(ALLOWED.items()))
def test_a_subpackage_imports_only_what_it_is_allowed_to(subpackage: str, allowed: set[str]):
    assert list((INFER / subpackage).rglob("*.py")), subpackage
    assert [(f, n, t) for f, n, t in _imports_of(subpackage) if t not in allowed] == []


def test_every_subpackage_is_in_the_table():
    on_disk = {p.name for p in INFER.iterdir() if p.is_dir() and p.name != "__pycache__"}
    assert on_disk == set(ALLOWED)


def test_the_table_has_no_cycle():
    # A subpackage's allowed imports must themselves be listed strictly below it.
    done: set[str] = set()
    remaining = dict(ALLOWED)
    while remaining:
        ready = [name for name, deps in remaining.items() if deps <= done]
        assert ready, f"cycle among {sorted(remaining)}"
        for name in ready:
            done.add(name)
            del remaining[name]


def test_checker_resolves_relative_imports_between_subpackages():
    # `from . import jsonl` is the file's own subpackage: reported here, filtered by the callers.
    source = "from ..contract import Ruling\nfrom ...layout import STATE_DIR\nfrom . import jsonl\n"
    assert infer_siblings(source, "slop.infer.ledger.interface", is_package=False) == [
        (1, "contract"), (3, "ledger")]


def test_checker_catches_a_planted_upward_import():
    hits = infer_siblings("from ..apply import route\n", "slop.infer.contract.schema", is_package=False)
    assert [t for _, t in hits if t not in ALLOWED["contract"]] == ["apply"]
