"""Make ``scratch.lexicon`` importable when pytest runs from any cwd.

Inserts the repo root onto sys.path so ``from scratch.lexicon
import Lexeme`` resolves regardless of where pytest was invoked.
"""
from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
