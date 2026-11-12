"""``slop ontology``: the project's vocabulary, what its words mean, and how it corrects the code.

``draft`` seeds it with the words the code declares (keeping what is agreed), ``check``
validates it, ``show WORD`` prints a term with its links, ``occurrences WORD`` lists the declared
names a word reaches, and ``rename OLD NEW`` lists every edit a rename makes.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from .. import ontology
from ..ontology import draft as seed, occurrence
from . import resolve
from .render import add_output, header

#: the command, as its views label themselves
_COMMAND = "ontology"


def register(sub) -> None:
    p_onto = sub.add_parser(_COMMAND, help="the project's vocabulary: what its words mean")
    onto_sub = p_onto.add_subparsers(dest="ontology_command", required=True)
    p_draft = onto_sub.add_parser("draft", help="add every word the code declares as a term to define; keeps agreed terms")
    resolve.add_root(p_draft)
    p_draft.set_defaults(run=lambda a: draft(a.root))
    p_check = onto_sub.add_parser("check", help="validate the vocabulary (SKOS integrity, one word per term)")
    resolve.add_root(p_check)
    p_check.set_defaults(run=lambda a: check(a.root))
    p_show = onto_sub.add_parser("show", help="print what a word means and how it relates to others")
    p_show.add_argument("word")
    resolve.add_root(p_show)
    add_output(p_show)
    p_show.set_defaults(run=lambda a: show(a.word, a.root, a.output))
    p_where = onto_sub.add_parser("occurrences", help="the declared names a word reaches")
    p_where.add_argument("word")
    resolve.add_root(p_where)
    add_output(p_where)
    p_where.set_defaults(run=lambda a: occurrences(a.word, a.root, a.output))
    p_rename = onto_sub.add_parser("rename", help="every edit that renaming a word in declared names makes (prints, never writes)")
    p_rename.add_argument("old")
    p_rename.add_argument("new")
    resolve.add_root(p_rename)
    add_output(p_rename)
    p_rename.set_defaults(run=lambda a: rename(a.old, a.new, a.root, a.output))


def draft(root: str | Path) -> int:
    """Write the vocabulary with every word the code declares and it does not yet hold."""
    corpus = resolve.scan(root)
    if corpus is None:
        return 2
    file = resolve.ontology_path(root)
    try:
        existing = ontology.load(file) if file.exists() else None
    except ontology.OntologyError as exc:
        print(f"slop: error: {exc}", file=sys.stderr)
        return 2
    scheme = seed.draft(corpus.lexicon(), existing, file.parent.parent.resolve().name.lower() or "project")
    ontology.save(scheme, file)
    added = len(scheme.terms) - (len(existing.terms) if existing else 0)
    print(f"{file}  {len(scheme.terms)} terms ({added} new), {len(scheme.defined())} defined")
    return 0


def occurrences(word: str, root: str | Path, output: str = "human") -> int:
    """The declared names ``word`` reaches. Exit 0 whether or not there are any."""
    corpus = resolve.scan(root)
    if corpus is None:
        return 2
    found = occurrence.occurrences(word, corpus)
    if output == "json":
        print(json.dumps({"word": word, "occurrences": [vars(o) for o in found]}, indent=2))
        return 0
    lines = [header(_COMMAND, word, f"{len(found)} declared name(s)")]
    lines += [f"  {o.role:<9} {o.identifier}  {resolve.relative(o.path, corpus)}:{o.line}" for o in found]
    print("\n".join(lines))
    return 0


def rename(old: str, new: str, root: str | Path, output: str = "human") -> int:
    """Every edit that renaming the word ``old`` to ``new`` makes. Nothing is written."""
    corpus = resolve.scan(root)
    if corpus is None:
        return 2
    edits = occurrence.rename(old, new, corpus)
    if output == "json":
        print(json.dumps({"old": old, "new": new, "edits": [vars(e) for e in edits]}, indent=2))
        return 0
    lines = [header(_COMMAND, f"{old} -> {new}", f"{len(edits)} edit(s)")]
    lines += [f"  {resolve.relative(e.path, corpus)}:{e.line}:{e.column}  {e.before} -> {e.after}" for e in edits]
    print("\n".join(lines))
    return 0


def check(root: str | Path) -> int:
    """Exit 0 when the vocabulary is consistent, 1 with problems (each printed), 2 when unreadable."""
    file = resolve.ontology_path(root)
    try:
        scheme = ontology.load(file)
    except ontology.OntologyError as exc:
        print(f"slop: error: {exc}", file=sys.stderr)
        return 2
    found = ontology.problems(scheme)
    for problem in found:
        print(f"{file}: {problem}")
    print(f"{file}  {len(scheme.terms)} terms, {len(scheme.defined())} defined, {len(found)} problem(s)")
    return 1 if found else 0


def show(word: str, root: str | Path, output: str = "human") -> int:
    """What ``word`` means: its term, definition, labels and links. Exit 0 whether or not it is a term."""
    scheme = ontology.load(resolve.ontology_path(root))
    term = scheme.term(word)
    if output == "json":
        entry = ontology.dump(ontology.Scheme(scheme.name, [term]))["terms"][0] if term else None
        narrower = [t.pref_label for t in scheme.narrower(term.pref_label)] if term else []
        print(json.dumps({"word": word, "term": entry, "narrower": narrower}, indent=2))
        return 0
    if term is None:
        print(header(_COMMAND, word, f"not a term in {scheme.name}"))
        return 0
    lines = [header(_COMMAND, term.pref_label, "defined" if term.defined else "undefined (a draft candidate)"),
             f"  {term.definition}" if term.defined else "  (no definition yet)"]
    for name, values in (("also", term.alt_labels), ("retired", term.hidden_labels), ("broader", term.broader),
                         ("narrower", tuple(t.pref_label for t in scheme.narrower(term.pref_label))),
                         ("related", term.related)):
        if values:
            lines.append(f"  {name}: {', '.join(values)}")
    print("\n".join(lines))
    return 0
