"""Grep kernel - pattern search using ripgrep."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from slop._aux.util.subprocess import run_tool


@dataclass
class GrepMatch:
    """A single match from grep search."""

    path: str
    line_number: int
    content: str
    pattern: str
    context_before: list[str] = field(default_factory=list)
    context_after: list[str] = field(default_factory=list)


@dataclass
class GrepResult:
    """Aggregated grep results."""

    matches: list[GrepMatch]
    files_with_matches: int
    total_matches: int
    patterns_searched: list[str]
    errors: list[str] = field(default_factory=list)
    truncated: bool = False


def grep_kernel(
    patterns: list[dict],
    root: Path,
    *,
    files: list[Path] | None = None,
    globs: list[str] | None = None,
    excludes: list[str] | None = None,
    mode: Literal["regex", "fixed"] = "regex",
    case: Literal["smart", "sensitive", "insensitive"] = "smart",
    context_lines: int = 0,
    hidden: bool = False,
    no_ignore: bool = False,
    max_matches: int | None = None,
    parallelism: int = 4,
) -> GrepResult:
    """Search for patterns in files using ripgrep.

    Args:
        patterns: List of {"kind": "regex"|"fixed", "value": "pattern"}
        root: Search root directory
        files: Optional pre-filtered file list (pipeline mode)
        globs: Include glob patterns
        excludes: Exclude glob patterns
        mode: Default pattern mode
        case: Case sensitivity
        context_lines: Lines of context around matches
        hidden: Search hidden files
        no_ignore: Don't respect gitignore
        max_matches: Maximum matches to return
        parallelism: Number of parallel searches

    Returns:
        GrepResult with matches and metadata
    """
    globs = globs or []
    excludes = excludes or []

    all_matches: list[GrepMatch] = []
    errors: list[str] = []
    files_seen: set[str] = set()

    def search_pattern(pattern_spec: dict) -> tuple[list[GrepMatch], str | None]:
        """Search for a single pattern."""
        kind = pattern_spec.get("kind", mode)
        value = pattern_spec["value"]

        args = _build_rg_args(
            pattern=value,
            kind=kind,
            globs=globs,
            excludes=excludes,
            case=case,
            context_lines=context_lines,
            hidden=hidden,
            no_ignore=no_ignore,
            files=files,
        )

        result = run_tool(args, cwd=root)

        if result.returncode not in (0, 1):  # 1 = no matches
            return [], result.stderr.strip() if result.stderr else None

        matches = _parse_rg_output(result.stdout, value)
        return matches, None

    # Run searches in parallel
    with ThreadPoolExecutor(max_workers=parallelism) as executor:
        futures = {
            executor.submit(search_pattern, p): p["value"]
            for p in patterns
        }

        for future in as_completed(futures):
            matches, error = future.result()
            if error:
                errors.append(error)
            all_matches.extend(matches)
            for m in matches:
                files_seen.add(m.path)

    # Apply max_matches limit
    truncated = False
    if max_matches and len(all_matches) > max_matches:
        all_matches = all_matches[:max_matches]
        truncated = True

    return GrepResult(
        matches=all_matches,
        files_with_matches=len(files_seen),
        total_matches=len(all_matches),
        patterns_searched=[p["value"] for p in patterns],
        errors=errors,
        truncated=truncated,
    )


def _build_rg_args(
    pattern: str,
    kind: str,
    globs: list[str],
    excludes: list[str],
    case: str,
    context_lines: int,
    hidden: bool,
    no_ignore: bool,
    files: list[Path] | None,
) -> list[str]:
    """Build ripgrep command arguments."""
    args = ["rg", "--line-number", "--with-filename", "--no-heading"]

    if kind == "fixed":
        args.append("--fixed-strings")

    if case == "sensitive":
        args.append("--case-sensitive")
    elif case == "insensitive":
        args.append("--ignore-case")
    # smart case is default for rg

    if context_lines > 0:
        args.extend(["--context", str(context_lines)])

    if hidden:
        args.append("--hidden")

    if no_ignore:
        args.append("--no-ignore")

    # Add globs (only if not using pre-filtered files)
    if not files:
        for g in sorted(globs):
            args.extend(["--glob", g])
        for e in sorted(excludes):
            args.extend(["--glob", f"!{e}"])

    args.append("--")
    args.append(pattern)

    # Use pre-filtered files or search current directory
    if files:
        for f in files:
            args.append(str(f))
    else:
        args.append(".")

    return args


def _parse_rg_output(output: str, pattern: str) -> list[GrepMatch]:
    """Parse ripgrep output into match objects."""
    matches = []

    for line in output.strip().split("\n"):
        if not line:
            continue

        # Format: file:line:content
        parts = line.split(":", 2)
        if len(parts) >= 3:
            try:
                matches.append(GrepMatch(
                    path=parts[0],
                    line_number=int(parts[1]),
                    content=parts[2],
                    pattern=pattern,
                ))
            except (ValueError, IndexError):
                continue

    return matches
