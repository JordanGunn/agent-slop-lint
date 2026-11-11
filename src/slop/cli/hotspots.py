"""``slop hotspots``: files changed in a revision window, ranked by churn x complexity (Tornhill 2015)."""
from __future__ import annotations

import json
from pathlib import Path

from ..metrics.structural.hotspots import DEFAULT_LAST
from ..metrics.structural.view import Structure
from .render import add_output, header
from .resolve import add_root, scan


def register(sub) -> None:
    p_hot = sub.add_parser("hotspots", help="files ranked by recent churn x complexity")
    add_root(p_hot)
    window = p_hot.add_mutually_exclusive_group()
    window.add_argument("--since", default=None, metavar="REV",
                        help="commits in REV..HEAD plus uncommitted changes (HEAD = uncommitted only)")
    window.add_argument("--last", type=int, default=None, metavar="N",
                        help=f"the last N commits plus uncommitted changes (default {DEFAULT_LAST})")
    add_output(p_hot)
    p_hot.set_defaults(run=lambda a: view(a.root, a.output, since=a.since, last=a.last))


def view(root: str | Path, output: str = "human", *, since: str | None = None, last: int | None = None) -> int:
    """The window is revisions, not time: ``--since REV`` or ``--last N`` commits, plus every
    uncommitted change. No limit is applied; the list is the answer."""
    corpus = scan(root)
    if corpus is None:
        return 2
    if last is None:
        last = DEFAULT_LAST
    rows = Structure.over(corpus).hotspots(since=since, last=last)
    window = f"{since}..HEAD + uncommitted" if since is not None else f"last {last} commits + uncommitted"
    if output == "json":
        print(json.dumps({"window": window, "files": [
            {"path": h.path, "churn": h.churn, "complexity": h.complexity,
             "product": h.churn * h.complexity} for h in rows]}, indent=2))
        return 0
    lines = [header("hotspots", window, f"{len(rows)} file(s) changed")]
    lines += [f"  {h.path}  churn {h.churn} x complexity {h.complexity} = {h.churn * h.complexity}" for h in rows]
    print("\n".join(lines))
    return 0
