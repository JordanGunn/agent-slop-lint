"""``slop skill``: the Agent Skills that teach an agent to use slop."""
from __future__ import annotations

import sys
from pathlib import Path

from ..skill.catalog import SKILLS
from ..skill.install import InstallError, install as install_skill


def register(sub) -> None:
    p_skill = sub.add_parser("skill", help="Agent Skills that teach an agent to use slop")
    skill_sub = p_skill.add_subparsers(dest="skill_command", required=True)
    skill_sub.add_parser("list", help="list the skills slop ships").set_defaults(run=lambda a: catalog())
    p_show = skill_sub.add_parser("show", help="print a skill's SKILL.md, or one of its files")
    p_show.add_argument("name")
    p_show.add_argument("file", nargs="?", default=None, help="a path inside the skill (default: SKILL.md)")
    p_show.set_defaults(run=lambda a: show(a.name, a.file))
    p_install = skill_sub.add_parser("install", help="write a skill's directory under DEST")
    p_install.add_argument("name")
    p_install.add_argument("--dest", required=True, help="the skills directory, e.g. .claude/skills")
    p_install.add_argument("--force", action="store_true", help="replace an existing install of this skill")
    p_install.set_defaults(run=lambda a: install(a.name, a.dest, a.force))


def catalog() -> int:
    """List the skills slop ships."""
    for name, skill in sorted(SKILLS.items()):
        print(f"{name}  {skill.description}")
    return 0


def show(name: str, file: str | None) -> int:
    """Print a skill's SKILL.md, or the file at ``file`` inside it."""
    skill = _skill(name)
    if skill is None:
        return 2
    tree = skill.tree()
    shown = "SKILL.md" if file is None else file
    if shown not in tree:
        print(f"slop: error: skill '{name}' has no file '{shown}'. Its files: {', '.join(tree)}", file=sys.stderr)
        return 2
    print(tree[shown], end="")
    return 0


def install(name: str, dest: str, force: bool) -> int:
    """Write a skill's directory under ``dest`` and print where."""
    skill = _skill(name)
    if skill is None:
        return 2
    try:
        print(install_skill(skill, Path(dest), replace=force))
    except InstallError as exc:
        print(f"slop: error: {exc}", file=sys.stderr)
        return 2
    return 0


def _skill(name: str):
    """The skill called ``name``, or None after printing why there is none."""
    if name not in SKILLS:
        print(f"slop: error: no skill '{name}'. Try `slop skill list`.", file=sys.stderr)
        return None
    return SKILLS[name]
