"""Runt-package detection — a package boundary that doesn't earn its weight.

Legacy: structure.runts. A runt is a package directory with exactly one non-init
module, no subpackages, and a *trivial* ``__init__`` (imports / re-exports only,
no composition logic). The namespace level then adds no semantic payload — the lone
module could sit flat at the parent level under the package's name.

This is a filesystem-topology signal, not a content one: it is identified purely by
weight in the project tree. The package-init convention is a per-language *fact*
(``grammar.package_init_name``); languages with no init-file package convention
return ``None`` and are structurally N/A (never a runt).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

_MAX_INIT_SUBSTANTIVE_LINES = 5


def is_runt(package: Any, *, max_init_lines: int = _MAX_INIT_SUBSTANTIVE_LINES) -> bool:
    grammar = _grammar_of(package)
    init_name = grammar.package_init_name() if grammar is not None else None
    if init_name is None:
        return False  # no init-file package convention → structurally N/A

    mods = list(package.modules())
    init_mods = [m for m in mods if m.files and m.files[0].name == init_name]
    real_mods = [m for m in mods if m not in init_mods]
    # A runt has exactly one real module behind an init boundary.
    if len(init_mods) != 1 or len(real_mods) != 1:
        return False
    if _has_subpackage(package.path, init_name):
        return False
    return _init_is_trivial(init_mods[0], max_init_lines)


def _grammar_of(package: Any) -> Any:
    mods = package.modules()
    return mods[0]._grammar if mods else None


def _has_subpackage(directory: Path, init_name: str) -> bool:
    """True if any direct subdirectory is itself a package (holds the init file)."""
    try:
        return any((sub / init_name).is_file() for sub in directory.iterdir() if sub.is_dir())
    except OSError:
        return False


def _init_is_trivial(init_module: Any, max_lines: int) -> bool:
    """True if the init module is mostly imports / re-exports — no composition logic.

    A line is "substantive" unless it is blank, a comment, a docstring line, an
    import, or a dunder assignment (``__all__``/``__version__``). Few substantive
    lines = the package adds nothing on top of its sole module.
    """
    text = init_module._content.decode("utf-8", errors="replace")
    substantive = 0
    in_docstring = False
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith('"""') or line.startswith("'''"):
            quote = line[:3]
            if line.count(quote) >= 2 and line != quote:  # single-line docstring
                continue
            in_docstring = not in_docstring
            continue
        if in_docstring:
            continue
        if line.startswith("from ") or line.startswith("import "):
            continue
        if line.startswith("__") and "=" in line:  # __all__ = [...], __version__ = "..."
            continue
        substantive += 1
    return substantive <= max_lines
