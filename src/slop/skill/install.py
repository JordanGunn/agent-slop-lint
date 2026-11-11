"""Write a skill's directory."""
from __future__ import annotations

import shutil
from pathlib import Path

from .model import Skill


class InstallError(Exception):
    """The skill could not be written where it was asked to go."""


def install(skill: Skill, parent: Path, *, replace: bool = False) -> Path:
    """Write ``skill`` to ``parent/<skill.name>/`` and return that directory.

    An existing directory is an error unless ``replace``, which removes it first: an installed
    skill is generated, so replacing it is how it is updated."""
    target = parent / skill.name
    if target.exists() or target.is_symlink():
        if not replace:
            raise InstallError(f"{target} exists; use --force to replace it")
        if not target.is_dir() or target.is_symlink():
            raise InstallError(f"{target} is not a skill directory; not replacing it")
        shutil.rmtree(target)
    for relative, text in skill.tree().items():
        path = target / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return target
