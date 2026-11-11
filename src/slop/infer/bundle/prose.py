"""Read the bundled prose: the instructions, and the references (rubrics among them)."""
from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).parent

_REFERENCES_DIR = "references"
_VERSION_LENGTH = 12


def instructions() -> str:
    """The agent's instructions for the inference workflow."""
    return (ROOT / "instructions.md").read_text(encoding="utf-8")


def references() -> tuple[str, ...]:
    """The name of every reference, sorted: its path under ``references/`` without ``.md``."""
    base = ROOT / _REFERENCES_DIR
    return tuple(sorted(p.relative_to(base).with_suffix("").as_posix() for p in base.rglob("*.md")))


def reference(name: str) -> str:
    """The text of the reference called ``name``. Raises ``KeyError`` for an unknown name."""
    return _path(name).read_text(encoding="utf-8")


def reference_version(name: str) -> str:
    """A hash of the reference's content. It changes exactly when the text does."""
    return hashlib.sha256(_path(name).read_bytes()).hexdigest()[:_VERSION_LENGTH]


def _path(name: str) -> Path:
    if name not in references():            # only listed names: no path of the caller's choosing
        raise KeyError(name)
    return ROOT / _REFERENCES_DIR / f"{name}.md"
