"""``slop doctor`` — print the status of each system binary slop shells out to."""
from __future__ import annotations

import sys

from slop import __version__
from slop.cli.color import bold, green, red


def add_parser(subparsers) -> None:
    """Register the ``doctor`` subcommand."""
    subparsers.add_parser(
        "doctor",
        help="Check that required system binaries (fd, git, rg) are installed",
    )


def cmd_doctor() -> int:
    """Print binary statuses. Exits 2 if any of fd/git/rg are missing."""
    from slop.doctor import run_doctor

    report = run_doctor()
    tools = report.get("tools", {})

    print(bold(f"slop doctor — slop {__version__}"))
    print("")

    all_present = True
    for name in ("fd", "rg", "git"):
        info = tools.get(name)
        if info is None:
            continue
        line, present = _format_binary_status(name, info)
        print(line)
        if not present:
            all_present = False

    print("")
    if all_present:
        print(green(bold("All required binaries are installed.")))
        return 0
    print(red(bold("Missing dependencies. See above for install instructions.")))
    return 2


def _format_binary_status(name: str, info: dict) -> tuple[str, bool]:
    """Format one binary's doctor line. Returns (line, is_present)."""
    if info.get("available", False):
        path = info.get("path", "")
        version = info.get("version") or ""
        actual_name = info.get("actual_name")
        alias = f" (as {actual_name})" if actual_name else ""
        version_str = f" ({version})" if version else ""
        return f"  {green(chr(0x2713))} {bold(name):20s} {path}{alias}{version_str}", True
    install = info.get("install", "")
    line = f"  {red(chr(0x2717))} {bold(name):20s} missing"
    if install:
        line += f" — install: {install}"
    return line, False


# Suppress unused stderr import warning at module level — kept for future error paths.
_ = sys
