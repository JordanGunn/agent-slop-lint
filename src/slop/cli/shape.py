"""``slop shape``: each class's Chidamber-Kemerer profile and method groups."""
from __future__ import annotations

import json
from pathlib import Path

from ..metrics.structural.view import Structure
from ..scope import find
from ..scope.find import walk
from ..scope.identity import ScopeKind
from .render import add_output, header, label, where
from . import resolve
from .resolve import add_root, add_scope, scan


def register(sub) -> None:
    p_shape = sub.add_parser("shape", help="print each class's CK profile and cohesion groups")
    add_root(p_shape)
    add_scope(p_shape, "qualname or path of the scope to report beneath")
    add_output(p_shape)
    p_shape.set_defaults(run=lambda a: view(a.root, a.output, scope=a.scope, scope_kind=a.scope_kind))


def view(root: str | Path, output: str = "human", *, scope: str | None = None,
         scope_kind: str | None = None) -> int:
    """Every class beneath a scope, unfiltered: no limits are applied, so it answers for any
    class (the ``class-*`` rules apply limits to the same numbers). ``lcom4`` is ``null``
    where the language's instance member access cannot be read from syntax."""
    corpus = scan(root)
    if corpus is None:
        return 2
    target = resolve.target(corpus, scope, scope_kind)
    if target is None:
        return 2
    located = find.locate((s for s in walk(target) if s.id.kind is ScopeKind.CLASS), corpus.root)
    rows = [(match, Structure.over(cls).ck().as_dict()) for cls, match in located]
    notes = find.caveats(corpus, ScopeKind.CLASS, under=target)
    name = label(target, corpus)
    if output == "json":
        print(json.dumps({"scope": name, "kind": target.id.kind.value,
                          "classes": [{**match.as_dict(), **ck} for match, ck in rows],
                          "caveats": notes}, indent=2))
        return 0
    lines = [header("shape", f"{name} ({target.id.kind.value})", f"{len(rows)} class(es)")]
    for match, ck in rows:
        lines += _class(match, ck)
    lines += [f"  note: {n}" for n in notes]
    print("\n".join(lines))
    return 0


def _class(match, ck: dict) -> list[str]:
    """One class: its CK numbers, then its method groups, detached methods and caveats."""
    lcom4 = "n/a" if ck["lcom4"] is None else ck["lcom4"]
    lines = [f"  {match.name}  {where(match)}  nom {ck['nom']} dit {ck['dit']} "
             f"noc {ck['noc']} cbo {ck['cbo']} lcom4 {lcom4}"]
    if ck["method_groups"]:
        lines.append("    groups: " + " ".join("{" + ", ".join(g) + "}" for g in ck["method_groups"]))
    if ck["detached"]:
        lines.append("    detached: " + ", ".join(ck["detached"]))
    lines += [f"    note: {c}" for c in ck["caveats"]]
    return lines
