"""``slop ast``: the parse tree of one source file."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from ..ast import GRAMMARS_BY_ID
from ..ast.parse import detect_language
from ..ast.tree import AST
from .render import add_output, header


def register(sub) -> None:
    p_ast = sub.add_parser("ast", help="print the parse tree of a single source file")
    p_ast.add_argument("path", help="source file to inspect")
    add_output(p_ast)
    p_ast.add_argument("--raw", action="store_true",
                       help="keep anonymous tokens (full transcript); default is the named skeleton")
    p_ast.add_argument("--max-depth", type=int, default=None, help="truncate the tree below this depth")
    p_ast.set_defaults(run=lambda a: view(a.path, a.output, raw=a.raw, max_depth=a.max_depth))


def view(path: str | Path, output: str = "human", *, raw: bool = False, max_depth: int | None = None) -> int:
    """Print the named-node skeleton of ``path``, or with ``raw`` every anonymous token too."""
    ast = _parse(Path(path))
    if ast is None:
        return 2
    if output == "json":
        print(json.dumps(ast.root.to_dict(named_only=not raw, max_depth=max_depth), indent=2))
        return 0
    body = ast.render(named_only=not raw, max_depth=max_depth)
    print(header("ast", str(path), f"{body.count(chr(10)) + 1} nodes"))
    print(body)
    return 0


def _parse(path: Path) -> AST | None:
    """The parse tree of ``path``, or None after printing why there is none."""
    if not path.exists():
        print(f"slop: error: path does not exist: {path}", file=sys.stderr)
        return None
    if path.is_dir():
        print(f"slop: error: {path} is a directory; ast takes a single file", file=sys.stderr)
        return None
    language = detect_language(path)
    if language is None or language not in GRAMMARS_BY_ID:
        print(f"slop: error: no grammar for {path} (unrecognised language)", file=sys.stderr)
        return None
    ast = AST.parse(path, GRAMMARS_BY_ID[language])
    if ast is None:
        print(f"slop: error: could not parse {path}", file=sys.stderr)
    return ast
