"""Shared fixtures."""
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def sample_project(tmp_path: Path) -> Path:
    """A small project with the vocabulary shapes the primitives must answer about.

    ``Index`` is defined in two sibling modules, ``Store`` in two more, ``Address`` once,
    and ``Thing`` is a function (not a class). ``a/mod.py`` and ``b/mod.py`` share the bare
    module stem ``mod`` and each define ``Twin``, so qualname alone cannot tell them apart.
    """
    files = {
        "index/__init__.py": "",
        "index/octree.py": '"""Octree."""\n\nclass Index:\n    pass\n',
        "index/quadtree.py": "class Index:\n    pass\n",
        "store/__init__.py": "",
        "store/array.py": "class Store:\n    def save(self):\n        return 1\n",
        "store/frame.py": "class Store:\n    def save(self):\n        return 2\n",
        "store/address.py": "class Address:\n    pass\n",
        "thing.py": "def Thing():\n    return 1\n",
        "a/__init__.py": "",
        "a/mod.py": "class Twin:\n    pass\n",
        "b/__init__.py": "",
        "b/mod.py": "class Twin:\n    pass\n",
    }
    for rel, body in files.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body)
    return tmp_path
