"""The project's vocabulary: ``slop ontology draft|check`` write and validate it, ``slop vocab``
compares the code with it."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from ..config import AnalysisConfig
from ..layout import ONTOLOGY_FILENAME, STATE_DIR
from ..ontology import OntologyIR, compare
from ..ontology.draft import draft as draft_vocabulary
from ..ontology.ir import OntologyError
from ..rules import RULE_REGISTRY
from ..scope import find as discovery
from ..scope.identity import ScopeKind
from .render import add_output, header, where
from .resolve import add_root, project_root, scan


def register(sub) -> None:
    p_vocab = sub.add_parser("vocab", help="compare code names with a canonical ontology (JSON IR)")
    p_vocab.add_argument("--ontology", default=None, help="Open Ontology IR JSON file (default: the project's)")
    add_root(p_vocab)
    p_vocab.add_argument("--term", default=None, help="print this term's canonical entry instead of comparing")
    add_output(p_vocab)
    p_vocab.set_defaults(run=lambda a: vocab(a.root, a.ontology, a.output, term=a.term))

    p_onto = sub.add_parser("ontology", help="the project's vocabulary: draft it from the code, or check it")
    onto_sub = p_onto.add_subparsers(dest="ontology_command", required=True)
    p_draft = onto_sub.add_parser("draft", help="write the project's vocabulary, drafted from its classes")
    add_root(p_draft)
    p_draft.add_argument("--force", action="store_true", help="replace an existing vocabulary")
    p_draft.set_defaults(run=lambda a: draft(a.root, a.force))
    p_check = onto_sub.add_parser("check", help="validate the project's vocabulary")
    add_root(p_check)
    p_check.set_defaults(run=lambda a: check(a.root))


def path(root: str | Path) -> Path:
    """Where the project's vocabulary lives."""
    root = Path(root)
    return project_root(root, AnalysisConfig.load(root, RULE_REGISTRY)) / STATE_DIR / ONTOLOGY_FILENAME


def vocabulary(root: str | Path, ontology: str | Path | None) -> OntologyIR:
    """The vocabulary at ``ontology``, else the project's. Raises ``OntologyError`` if there is none."""
    file = Path(ontology) if ontology is not None else path(root)
    if ontology is None and not file.exists():
        raise OntologyError(f"no vocabulary at {file}; pass --ontology FILE or run `slop ontology draft`")
    return OntologyIR.load(file)


def draft(root: str | Path, force: bool) -> int:
    """Write the project's vocabulary, drafted from its classes."""
    corpus = scan(root)
    if corpus is None:
        return 2
    target = path(root)
    if target.exists() and not force:
        print(f"slop: error: {target} exists and holds agreed definitions; use --force to replace it",
              file=sys.stderr)
        return 2
    drafted = draft_vocabulary(corpus, name=target.parent.parent.resolve().name.lower() or "project")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(drafted.as_ir(), indent=2) + "\n", encoding="utf-8")
    described = sum(1 for t in drafted.terms() if t.description)
    print(f"{target}  {len(drafted.terms())} entities, {described} with a description")
    return 0


def check(root: str | Path) -> int:
    """Validate the project's vocabulary: exit 0 if Open Ontology would accept it, 2 if not."""
    try:
        loaded = vocabulary(root, None)
    except OntologyError as exc:
        print(f"slop: error: {exc}", file=sys.stderr)
        return 2
    print(f"{path(root)}  valid: {len(loaded.terms())} terms, {len(loaded.entities())} entities")
    return 0


def vocab(root: str | Path, ontology: str | Path | None, output: str = "human", *,
          term: str | None = None) -> int:
    """The canonical vocabulary against the code.

    ``--term NAME`` answers what NAME is canonically (no scan needed). Otherwise the
    classes found under ``--root`` are compared with the ontology's entities: matched,
    unknown to the ontology, and declared but unused. Exit 0 whenever the comparison ran;
    gating on mismatches belongs to the lint layer."""
    canonical = vocabulary(root, ontology)
    if term is not None:
        return _term(canonical, term, output)
    corpus = scan(root)
    if corpus is None:
        return 2
    result = compare(discovery.find(corpus, kind=ScopeKind.CLASS), canonical)
    notes = discovery.caveats(corpus, ScopeKind.CLASS)
    if output == "json":
        print(json.dumps({"vocabulary": canonical.name, **result.as_dict(), "caveats": notes}, indent=2))
        return 0
    lines = [header("vocab", canonical.name,
                    f"{len(result.matched)} matched · {len(result.unknown)} unknown · "
                    f"{len(result.unused)} unused")]
    lines += [f"  matched  {t.name}  <- " + ", ".join(m.qualname for m in ms) for t, ms in result.matched]
    lines += [f"  unknown  {m.name}  {where(m)}" for m in result.unknown]
    lines += [f"  unused   {t.name}" for t in result.unused]
    lines += [f"  note: {n}" for n in notes]
    print("\n".join(lines))
    return 0


def _term(canonical: OntologyIR, term: str, output: str) -> int:
    """What ``term`` is in ``canonical``."""
    found = canonical.term(term)
    if output == "json":
        print(json.dumps({"vocabulary": canonical.name, "query": term,
                          "canonical": found.as_dict() if found else None}, indent=2))
        return 0
    if found is None:
        print(header("vocab", term, f"not canonical in {canonical.name}"))
        return 0
    lines = [header("vocab", term, f"{found.kind.value} {found.name} in {canonical.name}")]
    if found.description:
        lines.append(f"  {found.description}")
    if found.fields:
        lines.append("  fields: " + ", ".join(found.fields))
    print("\n".join(lines))
    return 0
