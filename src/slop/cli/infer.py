"""``slop infer``: the exchange with an agent that rules on the linter's subjective findings."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from ..infer.apply.route import route
from ..infer.apply.settle import settle
from ..infer.bundle import prose
from ..infer.contract import ContractError, Verdicts, dump, parse, schemas
from ..infer.ledger.jsonl import JsonlLedger
from ..infer.source.finding import FindingSource
from .lint import analyse
from .resolve import add_root


def register(sub) -> None:
    p_infer = sub.add_parser("infer", help="inference over the linter's subjective findings: verdicts, rubrics, schemas")
    infer_sub = p_infer.add_subparsers(dest="infer_command", required=True)
    infer_sub.add_parser("instructions", help="print the agent's instructions for the inference workflow").set_defaults(
        run=lambda a: instructions())
    p_refs = infer_sub.add_parser("references", help="list the bundled references, or print one")
    p_refs.add_argument("name", nargs="?", default=None, help="a name from the list (for example rubrics/class-cohesion)")
    p_refs.set_defaults(run=lambda a: references(a.name))
    p_schema = infer_sub.add_parser("schema", help="print the JSON Schema of the documents the exchange uses")
    p_schema.add_argument("name", nargs="?", default=None, choices=sorted(schemas()),
                          help="one document (default: all)")
    p_schema.set_defaults(run=lambda a: schema(a.name))
    p_apply = infer_sub.add_parser("apply", help="store verdicts from a file or stdin and print a receipt")
    p_apply.add_argument("file", nargs="?", default="-", help="verdicts JSON (default: stdin)")
    add_root(p_apply)
    p_apply.set_defaults(run=lambda a: apply(a.file, a.root))


def instructions() -> int:
    """Print the agent's instructions for the inference workflow."""
    print(prose.instructions(), end="")
    return 0


def references(name: str | None) -> int:
    """List the bundled references, or print the one called ``name``."""
    if name is None:
        print("\n".join(prose.references()))
        return 0
    try:
        print(prose.reference(name), end="")
    except KeyError:
        print(f"slop: error: no reference '{name}'. Try `slop infer references`.", file=sys.stderr)
        return 2
    return 0


def schema(name: str | None) -> int:
    """Print the JSON Schema of every document an agent and slop exchange, or of one."""
    documents = schemas()
    print(json.dumps(documents if name is None else documents[name], indent=2))
    return 0


def apply(file: str, root: str | Path) -> int:
    """Read a verdicts document (a file, or ``-`` for stdin), store what is acceptable, and print
    the receipt. Exit 1 if any verdict was rejected, 2 if the document is not valid."""
    text = sys.stdin.read() if file == "-" else Path(file).read_text(encoding="utf-8")
    try:
        verdicts = parse(Verdicts, json.loads(text))
    except (json.JSONDecodeError, ContractError) as exc:
        print(f"slop: error: {exc}", file=sys.stderr)
        return 2
    analysis = analyse(root)
    if analysis is None:
        return 2
    ledger = JsonlLedger.at(analysis.root)
    inferable = {item.id: item for item in FindingSource().residue(analysis)} | settle(analysis, ledger).groups
    receipt = route(verdicts, inferable, ledger,
                    at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    print(json.dumps(dump(receipt), indent=2))
    return 1 if receipt.rejected else 0
