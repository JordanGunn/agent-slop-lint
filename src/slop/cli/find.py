"""``slop find``: where a name is defined, or which names are defined twice."""
from __future__ import annotations

import json
from pathlib import Path

from ..scope import find as discovery
from ..scope.identity import ScopeKind
from .render import add_output, header, where
from .resolve import add_root, parse_kind, scan


def register(sub) -> None:
    p_find = sub.add_parser("find", help="where a name is defined (or which names collide)")
    p_find.add_argument("name", nargs="?", default=None, help="exact local name to look up")
    add_root(p_find)
    p_find.add_argument("--kind", default=None, help="restrict to one scope kind (class, callable, ...)")
    p_find.add_argument("--collisions", action="store_true",
                        help="list names defined by more than one scope of --kind (default class)")
    add_output(p_find)
    p_find.set_defaults(run=lambda a: view(a.root, a.name, a.output, kind=a.kind, collisions=a.collisions))


def view(root: str | Path, name: str | None, output: str = "human", *,
         kind: str | None = None, collisions: bool = False) -> int:
    """A fact lookup: exact local name, optional kind. No match is an answer (exit 0)."""
    corpus = scan(root)
    if corpus is None:
        return 2
    scope_kind = parse_kind(kind)
    if collisions:
        return _collisions(corpus, scope_kind or ScopeKind.CLASS, output)
    if name is None:
        raise ValueError("find needs a NAME, or --collisions")
    found = discovery.find(corpus, name, kind=scope_kind)
    notes = discovery.caveats(corpus, scope_kind)
    if output == "json":
        print(json.dumps({"name": name, "matches": [m.as_dict() for m in found], "caveats": notes}, indent=2))
        return 0
    lines = [header("find", name, f"{len(found)} match(es)")]
    lines += [f"  {m.kind.value:<8} {m.qualname}  {where(m)}" for m in found]
    lines += [f"  note: {n}" for n in notes]
    print("\n".join(lines))
    return 0


def _collisions(corpus, kind: ScopeKind, output: str) -> int:
    """Every name more than one scope of ``kind`` defines."""
    groups = discovery.collisions(corpus, kind=kind)
    notes = discovery.caveats(corpus, kind)
    if output == "json":
        print(json.dumps({"kind": kind.value,
                          "collisions": {n: [m.as_dict() for m in ms] for n, ms in groups.items()},
                          "caveats": notes}, indent=2))
        return 0
    lines = [header("find", "collisions", f"{len(groups)} name(s) defined more than once")]
    for n, ms in groups.items():
        lines.append(f"  {n}  x{len(ms)}")
        lines += [f"    {m.qualname}  {where(m)}" for m in ms]
    lines += [f"  note: {n}" for n in notes]
    print("\n".join(lines))
    return 0
