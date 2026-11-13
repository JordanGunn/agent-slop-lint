"""``slop tree``: what a scope holds."""
from __future__ import annotations

import json
from pathlib import Path

from ..scope import find
from .render import add_output, header, label, where
from . import resolve
from .resolve import add_root, add_scope, parse_kind, scan


def register(sub) -> None:
    p_tree = sub.add_parser("tree", help="print the ownership tree beneath a scope")
    add_root(p_tree)
    add_scope(p_tree, "qualname or path of a sub-scope (default: whole corpus)")
    p_tree.add_argument("--depth", type=int, default=None, help="levels below the scope to show")
    p_tree.add_argument("--kind", default=None, help="show only scopes of this kind")
    add_output(p_tree)
    p_tree.set_defaults(run=lambda a: view(a.root, a.output, scope=a.scope, depth=a.depth,
                                           kind=a.kind, scope_kind=a.scope_kind))


def view(root: str | Path, output: str = "human", *, scope: str | None = None,
         depth: int | None = None, kind: str | None = None, scope_kind: str | None = None) -> int:
    """The ownership tree beneath a scope, one row per scope."""
    corpus = scan(root)
    if corpus is None:
        return 2
    target = resolve.target(corpus, scope, scope_kind)
    if target is None:
        return 2
    shown = parse_kind(kind)
    rows = find.outline(target, corpus.root, depth=depth, kinds=frozenset({shown}) if shown else None)
    notes = find.caveats(corpus, under=target)
    name = label(target, corpus)
    if output == "json":
        print(json.dumps({"scope": name, "kind": target.id.kind.value,
                          "rows": [{"level": level, **m.as_dict()} for level, m in rows],
                          "caveats": notes}, indent=2))
        return 0
    lines = [header("tree", f"{name} ({target.id.kind.value})", f"{len(rows)} scope(s)")]
    lines += [f"{'  ' * level}{m.kind.value} {m.name}  {where(m)}" for level, m in rows]
    lines += [f"  note: {n}" for n in notes]
    print("\n".join(lines))
    return 0
