"""Where a finding is, in terms that do not depend on how slop was invoked."""
from __future__ import annotations

from pathlib import Path


def project_path(path: Path | str, root: Path) -> str:
    """``path`` relative to the project ``root``, with ``/`` separators.

    Both are resolved first, so a relative spelling or a symlink gives the same answer. A path
    outside ``root`` comes back absolute."""
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(root.resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()
