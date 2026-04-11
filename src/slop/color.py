"""ANSI color helpers for terminal output.

Respects NO_COLOR env var (https://no-color.org/) and --no-color flag.
Auto-detects TTY — disables color when stdout is piped.
"""

from __future__ import annotations

import os
import sys

_enabled: bool | None = None


def _is_color_enabled() -> bool:
    """Check if color output should be used."""
    global _enabled
    if _enabled is not None:
        return _enabled
    if os.environ.get("NO_COLOR", "") != "":
        return False
    if not hasattr(sys.stdout, "isatty"):
        return False
    return sys.stdout.isatty()


def set_color(enabled: bool) -> None:
    """Force color on or off (called by CLI --no-color flag)."""
    global _enabled
    _enabled = enabled


def _wrap(code: str, text: str) -> str:
    if not _is_color_enabled():
        return text
    return f"\033[{code}m{text}\033[0m"


def red(text: str) -> str:
    return _wrap("31", text)


def green(text: str) -> str:
    return _wrap("32", text)


def yellow(text: str) -> str:
    return _wrap("33", text)


def bold(text: str) -> str:
    return _wrap("1", text)


def dim(text: str) -> str:
    return _wrap("2", text)
