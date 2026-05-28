"""structure.runts — package boundaries that don't earn their weight.

A package directory containing exactly one module (and no subpackages)
with a trivial ``__init__.py`` is structural overhead. The namespace
level adds no semantic payload — the single module could be flat at
the parent level under the package's name.

Detection signal (intentionally simple, top-down):
- Package directory (contains ``__init__.py``)
- Exactly one non-``__init__`` module inside
- No subdirectory packages
- ``__init__.py`` is small AND consists mostly of imports / re-exports
  (no substantial composition logic)

When all four hold, the package is a runt: undersized, weight-deficient,
should be absorbed into the parent namespace as a flat module.

Corrective action: ``FLATTEN_PACKAGE`` — rename the inner module to the
package's name and lift it up one level.

This rule operates at the structural-topology level. It does NOT examine
content cohesion (that's the decompositional concern handled by
``confusion``). A runt is identified purely by its weight in the
project tree, not by what's inside the module.

Currently Python-only (``__init__.py`` is hardcoded). The signal
generalises to any language with package/module distinction — the
init filename is a per-language convention.
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from slop.linter.rule import Rule
from slop.config import Config
from slop.linter.slop import Action, Slop
from slop.linter.tags import Tag
from slop.linter.types import RuleDefinition, RuleResult

if TYPE_CHECKING:
    pass


_RULE = Tag.RUNTS.key

_INIT_FILENAME = "__init__.py"


def _is_init_trivial(init_path: Path, max_substantive_lines: int) -> bool:
    """Return True if ``__init__.py`` is mostly imports / re-exports.

    A line is "substantive" if it isn't blank, a comment, a docstring
    line, an import statement, or a dunder assignment (``__all__``).
    Trivial init = few substantive lines = the package adds no
    composition logic on top of its sole module.
    """
    try:
        text = init_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False

    substantive = 0
    in_docstring = False
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            continue
        # Track triple-quoted docstrings (simplistic — handles the common case).
        if line.startswith('"""') or line.startswith("'''"):
            quote = line[:3]
            # Single-line docstring
            if line.count(quote) >= 2 and line != quote:
                continue
            in_docstring = not in_docstring
            continue
        if in_docstring:
            continue
        if line.startswith("from ") or line.startswith("import "):
            continue
        if line.startswith("__") and "=" in line:
            # __all__ = [...], __version__ = "...", etc.
            continue
        substantive += 1
    return substantive <= max_substantive_lines


def _walk_package_dirs(root: Path) -> list[Path]:
    """Find every directory under ``root`` that contains an ``__init__.py``."""
    out: list[Path] = []
    # Skip well-known directories that hold non-source content.
    skip_names = {"__pycache__", ".git", ".venv", "venv", "node_modules", ".pytest_cache"}
    stack: list[Path] = [root]
    while stack:
        d = stack.pop()
        try:
            entries = list(d.iterdir())
        except OSError:
            continue
        if (d / _INIT_FILENAME).is_file():
            out.append(d)
        for e in entries:
            if e.is_dir() and e.name not in skip_names and not e.name.startswith("."):
                stack.append(e)
    return out


def run(
    view, rule_config: Rule, slop_config: Config,
) -> RuleResult:
    """Flag package directories that don't earn their boundary.

    ``view`` (Structure or Lexicon, depending on dispatch) is not used —
    the rule walks the filesystem directly. The corrective concept is
    purely structural (file-tree topology), so parsed view data isn't
    the right input.
    """
    del view  # unused — filesystem walk only
    max_init_lines = int(rule_config.params.get("max_init_lines", 5))
    severity = rule_config.severity
    root = Path(slop_config.root).expanduser().resolve() if slop_config.root else Path.cwd()

    package_dirs = _walk_package_dirs(root)

    violations: list[Slop] = []
    packages_checked = 0
    for pkg_dir in sorted(package_dirs):
        packages_checked += 1
        init_path = pkg_dir / _INIT_FILENAME

        # Count direct child modules (excluding __init__).
        try:
            entries = list(pkg_dir.iterdir())
        except OSError:
            continue
        modules = [
            e for e in entries
            if e.is_file() and e.suffix == ".py" and e.name != _INIT_FILENAME
        ]
        # Subpackages: child directories containing __init__.py.
        subpackages = [
            e for e in entries
            if e.is_dir() and (e / _INIT_FILENAME).is_file()
        ]

        if len(modules) != 1 or subpackages:
            continue

        # Init must be trivial — no substantive composition logic.
        if not _is_init_trivial(init_path, max_init_lines):
            continue

        module = modules[0]
        pkg_name = pkg_dir.name
        module_name = module.stem
        pkg_rel = str(pkg_dir.relative_to(root)) if root else str(pkg_dir)
        suggested_name = f"{pkg_name}.py"

        prescription = (
            f"Flatten `{pkg_rel}/` into `{suggested_name}` at the "
            f"parent level. The package contains a single module "
            f"`{module_name}.py` with no subpackages, and the "
            f"`__init__.py` carries no composition logic — the "
            f"boundary adds a namespace level without semantic "
            f"payload. Move the module's contents to `{suggested_name}` "
            f"and delete the package directory."
        )

        violations.append(Slop(
            rule=_RULE,
            file=pkg_rel,
            line=None,
            symbol=pkg_name,
            message=(
                f"package `{pkg_rel}/` is a runt — single module "
                f"`{module_name}.py`, no subpackages, trivial `__init__.py`. "
                f"The boundary doesn't earn its weight."
            ),
            severity=severity,
            value=1,
            threshold=1,
            action=Action.FLATTEN_PACKAGE,
            prescription=prescription,
            confidence=0.8,
            scope="package",
            metadata={
                "package": pkg_rel,
                "module": module.name,
                "suggested_name": suggested_name,
            },
        ))

    return RuleResult(
        rule=_RULE,
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "packages_checked": packages_checked,
            "violation_count": len(violations),
        },
    )


RULE = RuleDefinition(
    name=_RULE,
    category=_RULE,
    description="Package directories with one module and trivial __init__ — boundary doesn't earn its weight",
    default_severity="warning",
    default_enabled=True,
    threshold_label="1 module + no subpackages + trivial init",
    run=run,
)
