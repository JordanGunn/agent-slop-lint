"""Resolving imports: the index of a corpus's modules that a grammar's ``resolve_import`` reads."""
from __future__ import annotations

import os
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def _normal(path: Path) -> Path:
    """``path`` with ``.`` and ``..`` collapsed, without touching the filesystem."""
    return Path(os.path.normpath(path))


@dataclass(frozen=True)
class ModuleIndex:
    """The corpus's modules, as an import can name them: ``by_name`` holds every spelling a
    module path can take (``find``, ``scope.find``, ``scope/find``, ...), ``by_path`` the
    module's file, with and without its suffix. Values are module ids."""

    by_name: dict[str, Any]
    by_path: dict[Path, Any]

    def at(self, path: Path) -> Any | None:
        """The module whose file is ``path`` (or ``path`` plus a suffix), else None."""
        return self.by_path.get(_normal(path))

    @staticmethod
    def keys(file: Path) -> tuple[Path, Path]:
        """The ``by_path`` keys of a module's file."""
        return _normal(file), _normal(file).with_suffix("")


def distinct(found: Iterable[Any]) -> tuple[Any, ...]:
    """The modules in ``found``, first occurrence kept, misses (None) dropped."""
    return tuple(dict.fromkeys(m for m in found if m is not None))
