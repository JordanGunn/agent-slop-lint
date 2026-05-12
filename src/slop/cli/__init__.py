"""``slop.cli`` — argparse-based CLI for slop.

Per-command files: ``cmd.py`` (root + lint), ``check.py``, ``init.py``,
``rules.py``, ``schema.py``, ``doctor.py``, and ``install/`` for nested
install targets.

``cmd.py`` is the convention for "root command of the bounding
package": it owns the parser and the main dispatcher. This
``__init__.py`` is a thin re-export so ``from slop.cli import main``
(used by ``slop.app:main``) keeps working.
"""
from __future__ import annotations

from .cmd import main

__all__ = ["main"]
