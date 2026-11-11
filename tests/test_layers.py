"""Layer boundaries — the import directions the architecture depends on.

The primitives (span, identity, lexicon, ast, metrics, ontology) must stay usable without
the lint layer above them, and the lint layer must not reach sideways into the CLI or the
vocabulary layer. Each rule below is a direction that holds today; the table is the
architecture, not a wish list. A violation names the file, line and package imported.

``scope`` reaches into ``metrics``/``graph`` only through the lazy imports in
``scope/carve.py`` that build the corpus analysis context; the table does not forbid that.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parent.parent / "src"

#: package -> the only internal packages it may import. Everything else is a violation.
ALLOWED: dict[str, set[str]] = {
    "span": set(),
    "identity": {"span"},
    "lexicon": {"span"},
    "ast": {"span"},
    "metrics": {"ast", "identity", "span"},          # never scope
    "ontology": {"lexicon", "scope", "span"},
    "lexical": {"lexicon", "ontology", "span"},      # never scope, rules or cli
    "layout": set(),
    "infer": {"dispatch", "identity", "layout", "span", "violation"},   # never cli or skill
    "skill": {"infer"},
}

#: package -> internal packages it must never import (everything else is unconstrained).
FORBIDDEN: dict[str, set[str]] = {
    "scope": {"rules", "rule", "dispatch", "cli", "ontology", "lexical"},
    "rules": {"cli", "ontology", "lexical"},
}


def test_only_the_cli_and_skill_import_infer():
    offenders = []
    for path in sorted((SRC / "slop").rglob("*.py")):
        rel = path.relative_to(SRC)
        if rel.parts[1] in ("infer", "skill", "cli.py"):
            continue
        module = ".".join(rel.with_suffix("").parts)
        is_package = path.name == "__init__.py"
        if is_package:
            module = module.removesuffix(".__init__")
        for line, target in internal_imports(path.read_text(), module, is_package=is_package):
            if target == "infer":
                offenders.append(f"{rel}:{line}")
    assert offenders == []


def internal_imports(source: str, module: str, *, is_package: bool) -> list[tuple[int, str]]:
    """``(line, top-level slop package)`` for every ``slop`` import in ``source``.

    ``module`` is the dotted module name (``slop.metrics.structural.view``); relative
    imports resolve against it. Imports inside functions count: a lazy import is still
    a dependency."""
    parts = module.split(".")
    base_of_file = parts if is_package else parts[:-1]
    found: list[tuple[int, str]] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ImportFrom):
            if node.level:
                base = base_of_file[: len(base_of_file) - (node.level - 1)]
            else:
                base = []
            if node.module:
                targets = [base + node.module.split(".")]
            else:
                targets = [base + [alias.name] for alias in node.names]
            for segs in targets:
                if len(segs) > 1 and segs[0] == "slop":
                    found.append((node.lineno, segs[1]))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                segs = alias.name.split(".")
                if len(segs) > 1 and segs[0] == "slop":
                    found.append((node.lineno, segs[1]))
    return found


def _package_files(package: str):
    """Source files that belong to ``package`` (a directory, or a single-file module)."""
    directory = SRC / "slop" / package
    if directory.is_dir():
        yield from sorted(directory.rglob("*.py"))
    elif (single := SRC / "slop" / f"{package}.py").exists():
        yield single


def _violations(package: str, bad) -> list[str]:
    out = []
    for path in _package_files(package):
        rel = path.relative_to(SRC)
        module = ".".join(rel.with_suffix("").parts)
        is_package = path.name == "__init__.py"
        if is_package:
            module = module.removesuffix(".__init__")
        for line, target in internal_imports(path.read_text(), module, is_package=is_package):
            if target != package and bad(target):
                out.append(f"{rel}:{line} imports slop.{target}")
    return out


@pytest.mark.parametrize("package,allowed", sorted(ALLOWED.items()))
def test_package_imports_only_what_it_is_allowed_to(package: str, allowed: set[str]):
    assert list(_package_files(package)), f"no source found for package '{package}'"
    assert _violations(package, lambda target: target not in allowed) == []


@pytest.mark.parametrize("package,forbidden", sorted(FORBIDDEN.items()))
def test_package_never_imports_what_is_forbidden_to_it(package: str, forbidden: set[str]):
    assert list(_package_files(package)), f"no source found for package '{package}'"
    assert _violations(package, lambda target: target in forbidden) == []


# ---- the checker itself ---------------------------------------------------

def test_checker_resolves_relative_imports_and_sees_lazy_ones():
    # In slop/metrics/structural/view.py, '...' is the slop package itself.
    source = (
        "from ...scope import find\n"           # relative, up to slop
        "def late():\n"
        "    from ...rules import x\n"          # lazy: still a dependency
        "import slop.cli\n"                     # absolute
        "import json\n"                         # not internal: ignored
    )
    found = internal_imports(source, "slop.metrics.structural.view", is_package=False)
    assert sorted(found) == [(1, "scope"), (3, "rules"), (4, "cli")]


def test_checker_resolves_one_dot_to_the_files_own_package():
    # In slop/metrics/structural/view.py, '..scope' means slop.metrics.scope: a metrics
    # import, not an import of the top-level scope package.
    assert internal_imports("from ..scope import x\n", "slop.metrics.structural.view",
                            is_package=False) == [(1, "metrics")]


def test_checker_resolves_from_dot_import_names_as_modules():
    # 'from .. import scope' inside slop/metrics/x.py names the sibling package 'scope'.
    assert internal_imports("from .. import scope\n", "slop.metrics.x", is_package=False) == [(1, "scope")]


def test_checker_catches_a_planted_violation():
    planted = "from ..scope import find\n"
    hits = internal_imports(planted, "slop.metrics.view", is_package=False)
    assert [target for _, target in hits if target not in ALLOWED["metrics"]] == ["scope"]
