"""Shared root-derivation helper for lexical rules."""
from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from slop.config import Config
    from slop.lexicon.view import Lexicon


def derive_root(lexicon: Lexicon, slop_config: Config) -> Path:
    """Prefer slop_config.root when explicitly set; otherwise fall back
    to the longest common directory across the lexicon's parses."""
    if slop_config.root and slop_config.root != ".":
        return Path(slop_config.root).expanduser().resolve()
    paths = [p.path for p in lexicon._parses]  # noqa: SLF001
    if paths:
        common = Path(os.path.commonpath([str(p) for p in paths]))
        return common.parent if common.is_file() else common
    if slop_config.root:
        return Path(slop_config.root).expanduser().resolve()
    return Path.cwd()
