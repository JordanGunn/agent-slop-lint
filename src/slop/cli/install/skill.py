"""``slop install skill <directory>`` — copy bundled agent skill files."""
from __future__ import annotations

import importlib.resources
import sys
from pathlib import Path


def add_parser(subparsers) -> None:
    """Register the ``install skill`` target."""
    parser = subparsers.add_parser(
        "skill",
        help="Install the slop agent skill into a directory",
        description="Copy the bundled slop agent skill files into the target directory.",
    )
    parser.add_argument(
        "directory", type=str,
        help="Target directory (created if it doesn't exist)",
    )


def cmd_skill(directory: str) -> int:
    """Run ``slop install skill <directory>``."""
    target = Path(directory)
    skill_pkg = importlib.resources.files("slop") / "_skill"

    target.mkdir(parents=True, exist_ok=True)

    try:
        count = _copy_tree(skill_pkg, target)
    except Exception as e:
        print(f"slop: failed to copy skill files: {e}", file=sys.stderr)
        return 2

    print(f"Installed slop skill ({count} files) → {target}")
    return 0


def _copy_tree(src, dst: Path) -> int:
    """Recursively copy from importlib resource to filesystem."""
    count = 0
    for item in src.iterdir():
        dest = dst / item.name
        if item.is_file():
            dest.write_bytes(item.read_bytes())
            count += 1
        elif item.is_dir():
            dest.mkdir(parents=True, exist_ok=True)
            count += _copy_tree(item, dest)
    return count
