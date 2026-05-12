"""``slop install hook`` — install or remove the git pre-commit hook."""
from __future__ import annotations

import stat
import subprocess
import sys
from pathlib import Path


_HOOK_MARKER = "# --- slop pre-commit hook ---"
_HOOK_CONTENT = f"""\
#!/bin/sh
{_HOOK_MARKER}
slop lint --output quiet
"""


def add_parser(subparsers) -> None:
    """Register the ``install hook`` target."""
    parser = subparsers.add_parser(
        "hook",
        help="Install or remove a git pre-commit hook that runs slop",
        description="Install a git pre-commit hook that runs slop lint before each commit.",
    )
    parser.add_argument(
        "--disable", action="store_true",
        help="Remove the slop pre-commit hook",
    )


def cmd_hook(disable: bool = False) -> int:
    """Run ``slop install hook [--disable]``."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        )
        repo_root = Path(result.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("slop: not inside a git repository", file=sys.stderr)
        return 2

    hook_path = repo_root / ".git" / "hooks" / "pre-commit"

    if disable:
        if not hook_path.exists():
            print("slop: no pre-commit hook to remove")
            return 0
        content = hook_path.read_text()
        if _HOOK_MARKER not in content:
            print("slop: pre-commit hook exists but was not installed by slop — leaving it alone")
            return 1
        hook_path.unlink()
        print(f"Removed slop pre-commit hook from {hook_path}")
        return 0

    if hook_path.exists():
        content = hook_path.read_text()
        if _HOOK_MARKER in content:
            print("slop: pre-commit hook already installed")
            return 0
        print(
            f"slop: {hook_path} already exists (not installed by slop)\n"
            f"Add this line manually to your existing hook:\n"
            f"  slop lint --output quiet",
            file=sys.stderr,
        )
        return 1

    hook_path.parent.mkdir(parents=True, exist_ok=True)
    hook_path.write_text(_HOOK_CONTENT)
    hook_path.chmod(hook_path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    print(f"Installed slop pre-commit hook → {hook_path}")
    return 0
