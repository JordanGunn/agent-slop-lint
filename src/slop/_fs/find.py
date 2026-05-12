"""Find kernel - file discovery using fd."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from slop._util.subprocess import run_tool, which


@dataclass
class FindEntry:
    """A discovered file or directory."""

    path: str
    type: Literal["file", "directory"]
    size: int | None = None


@dataclass
class FindResult:
    """Aggregated find results."""

    entries: list[FindEntry]
    total_found: int
    errors: list[str]


def find_kernel(
    root: Path,
    *,
    globs: list[str] | None = None,
    excludes: list[str] | None = None,
    type_filter: Literal["file", "directory", "any"] = "file",
    max_depth: int | None = None,
    hidden: bool = False,
    no_ignore: bool = False,
    max_results: int | None = None,
) -> FindResult:
    """Find files matching criteria using fd.

    Args:
        root: Search root directory
        globs: Include glob patterns
        excludes: Exclude glob patterns
        type_filter: Entry type filter
        max_depth: Maximum search depth
        hidden: Include hidden files
        no_ignore: Don't respect gitignore
        max_results: Maximum results to return

    Returns:
        FindResult with discovered entries
    """
    globs = globs or []
    excludes = excludes or []

    # Determine fd command name (fd vs fdfind on Debian/Ubuntu)
    fd_cmd = "fd"
    if not which("fd"):
        if which("fdfind"):
            fd_cmd = "fdfind"
        else:
            return FindResult(
                entries=[],
                total_found=0,
                errors=["fd not found. Install from https://github.com/sharkdp/fd"],
            )

    # fd's --glob is a mode-switch, not a repeatable key=value flag.
    # Passing multiple globs in a single invocation causes fd to interpret
    # the second and later patterns as search-path arguments, producing
    # "Search path '*.tsx' is not a directory" errors.
    #
    # Fix: run fd once per glob pattern, then merge and deduplicate.
    # When no globs are supplied, run fd exactly once without --glob (original
    # behaviour: match all files).
    invocations = globs if globs else [None]

    seen: dict[str, FindEntry] = {}
    errors: list[str] = []

    for glob in invocations:
        single_glob = [glob] if glob is not None else []
        args = _build_fd_args(
            fd_cmd=fd_cmd,
            globs=single_glob,
            excludes=excludes,
            type_filter=type_filter,
            max_depth=max_depth,
            hidden=hidden,
            no_ignore=no_ignore,
        )

        result = run_tool(args, cwd=root)

        if result.returncode != 0 and result.stderr:
            errors.append(result.stderr.strip())
            continue

        for entry in _parse_fd_output(result.stdout, type_filter):
            if entry.path not in seen:
                seen[entry.path] = entry

    if errors and not seen:
        return FindResult(entries=[], total_found=0, errors=errors)

    entries = list(seen.values())

    # Apply max_results cap across the full merged result set
    total_found = len(entries)
    if max_results and len(entries) > max_results:
        entries = entries[:max_results]

    return FindResult(
        entries=entries,
        total_found=total_found,
        errors=errors,
    )


def _build_fd_args(
    fd_cmd: str,
    globs: list[str],
    excludes: list[str],
    type_filter: str,
    max_depth: int | None,
    hidden: bool,
    no_ignore: bool,
) -> list[str]:
    """Build fd command arguments."""
    args = [fd_cmd]

    # Type filter
    if type_filter == "file":
        args.extend(["--type", "f"])
    elif type_filter == "directory":
        args.extend(["--type", "d"])

    if max_depth is not None:
        args.extend(["--max-depth", str(max_depth)])

    if hidden:
        args.append("--hidden")

    if no_ignore:
        args.append("--no-ignore")

    # Globs as patterns
    for g in globs:
        args.extend(["--glob", g])

    # Excludes
    for e in excludes:
        args.extend(["--exclude", e])

    return args


def _parse_fd_output(output: str, type_filter: str) -> list[FindEntry]:
    """Parse fd output into entry objects."""
    entries = []

    for line in output.strip().split("\n"):
        if not line:
            continue

        # Determine type based on trailing slash or filter
        entry_type: Literal["file", "directory"] = "file"
        if line.endswith("/"):
            entry_type = "directory"
            line = line.rstrip("/")
        elif type_filter == "directory":
            entry_type = "directory"

        entries.append(FindEntry(
            path=line,
            type=entry_type,
        ))

    return entries
