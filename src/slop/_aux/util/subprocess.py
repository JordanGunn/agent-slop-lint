"""Subprocess utilities for running external tools."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass
class ToolResult:
    """Result from running an external tool."""

    stdout: str
    stderr: str
    returncode: int
    command: list[str]

    @property
    def ok(self) -> bool:
        """Check if command succeeded."""
        return self.returncode == 0

    @property
    def lines(self) -> list[str]:
        """Get stdout as list of non-empty lines."""
        return [line for line in self.stdout.strip().split("\n") if line]


def run_tool(
    args: Sequence[str],
    *,
    cwd: Path | None = None,
    timeout: float | None = 60.0,
    check: bool = False,
) -> ToolResult:
    """Run an external tool and capture output.

    Args:
        args: Command and arguments
        cwd: Working directory
        timeout: Timeout in seconds (None = no timeout)
        check: Raise on non-zero exit

    Returns:
        ToolResult with captured output

    Raises:
        subprocess.TimeoutExpired: If timeout exceeded
        subprocess.CalledProcessError: If check=True and command fails
    """
    try:
        result = subprocess.run(
            list(args),
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=timeout,
            check=check,
        )
        return ToolResult(
            stdout=result.stdout,
            stderr=result.stderr,
            returncode=result.returncode,
            command=list(args),
        )
    except subprocess.CalledProcessError as e:
        return ToolResult(
            stdout=e.stdout or "",
            stderr=e.stderr or "",
            returncode=e.returncode,
            command=list(args),
        )


def which(name: str) -> Path | None:
    """Find executable in PATH.

    Args:
        name: Executable name

    Returns:
        Path to executable, or None if not found
    """
    import shutil

    path = shutil.which(name)
    return Path(path) if path else None
