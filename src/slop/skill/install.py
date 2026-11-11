"""Write a skill's directory, and replace only what slop itself wrote there.

Each install records the files it wrote in ``.slop-skill.json``. Replacing an install
(``--force``) requires that record for the same skill, overwrites the skill's files, removes
the files the previous install wrote that the skill no longer has, and leaves everything
else, such as notes a user added, where it is. The tree is built before anything on disk is
touched, so a failure to build it changes nothing.
"""
from __future__ import annotations

import json
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path, PurePosixPath

from .model import Skill

RECORD = ".slop-skill.json"


class InstallError(Exception):
    """The skill could not be written where it was asked to go."""


def install(skill: Skill, parent: Path, *, replace: bool = False) -> Path:
    """Write ``skill`` to ``parent/<skill.name>/`` and return that directory.

    An existing directory is an error unless ``replace``, and even then only an earlier install
    of the same skill, recognised by its record, is replaced."""
    tree = skill.tree()
    target = parent / skill.name
    previous: set[str] = set()
    if target.exists() or target.is_symlink():
        if not replace:
            raise InstallError(f"{target} exists; use --force to replace it")
        previous = _recorded_files(target, skill.name)
    for relative, text in tree.items():
        path = target / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    for relative in sorted(previous - set(tree)):
        _remove(target, relative)
    (target / RECORD).write_text(json.dumps(
        {"skill": skill.name, "slop": _slop_version(), "files": sorted(tree)}, indent=2) + "\n", encoding="utf-8")
    return target


def _recorded_files(target: Path, name: str) -> set[str]:
    """The files an earlier slop install of skill ``name`` wrote in ``target``."""
    if target.is_symlink() or not target.is_dir():
        raise InstallError(f"{target} is not a skill directory; not replacing it")
    try:
        record = json.loads((target / RECORD).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        record = None
    files = record.get("files") if isinstance(record, dict) else None
    if (not isinstance(record, dict) or record.get("skill") != name or not isinstance(files, list)
            or not all(isinstance(f, str) and _inside(f) for f in files)):
        raise InstallError(f"{target} was not installed by slop as '{name}'; not replacing it")
    return set(files)


def _inside(relative: str) -> bool:
    path = PurePosixPath(relative)
    return bool(relative) and not path.is_absolute() and ".." not in path.parts


def _remove(target: Path, relative: str) -> None:
    """Delete a file an earlier install wrote, then any directories it leaves empty."""
    path = target / relative
    if path.is_file() and not path.is_symlink():
        path.unlink()
    for directory in path.parents:
        if directory == target or not directory.is_dir() or any(directory.iterdir()):
            break
        directory.rmdir()


def _slop_version() -> str:
    try:
        return version("agent-slop-lint")
    except PackageNotFoundError:
        return "unknown"
