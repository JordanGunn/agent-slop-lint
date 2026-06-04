#!/usr/bin/env python
"""Measurement probe — do cross-module synonym-named functions exist, and does clone
detection corroborate them?

NOT a rule. Tests the hypothesis: two functions with the same object but a *synonymous
verb* in different modules (get_weather / fetch_weather) are likely the same thing — a
duplicate an agent introduces by picking a different verb each generation, invisible
without cross-file reading. The claim is that this is a battery: weak on names alone,
strong when structural clone detection also fires.

Three questions over a corpus:

  raw      — how many same-object / different-verb / cross-module function groups exist?
             (the unfiltered lexical signal; expected to be noisy — includes antonyms
             like get/set and coincidental object overlap.)
  synonym  — how many of those have two verbs in the SAME synonym class? (the curated
             precision layer; separates get/fetch from get/set.)
  battery  — how many synonym candidates ALSO co-occur in a Type-2 clone family? (the
             corroborated signal — the high-value find.)

Plus a clone-first view: of the real clone families, how are their members named
(identical verb / synonym verb / unrelated)? That says what fraction of real
duplicates the lexical signal could ever catch.

Run (from redesign/):  uv run python ../scripts/research/synonym_probe.py [--root R]
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path

from slop.metrics.lexical import Lexical
from slop.metrics.structural.view import Structure
from slop.scope import scan_corpus

DEFAULT_ROOT = "/home/jgodau/work/personal/slop/docs/.internal/snapshots/v1.2.0/slop"

# Curated action-verb synonym classes. A precision layer, not a prerequisite: the raw
# signal needs none of this. Within a class, verbs name the same operation; across
# classes (get vs set) they do not. Lifted from the kind of vocabulary v2 carried in
# lexicon/actions.py (dropped in v3); revive a fuller version if the signal earns it.
_SYNONYM_CLASSES = [
    {"get", "fetch", "retrieve", "load", "read", "pull", "obtain", "acquire"},
    {"create", "make", "build", "new", "construct", "generate", "produce"},
    {"delete", "remove", "drop", "destroy", "clear", "purge"},
    {"update", "set", "modify", "change", "edit", "mutate", "put"},
    {"check", "validate", "verify", "ensure", "assert", "is", "has"},
    {"find", "search", "lookup", "locate", "query", "resolve"},
    {"run", "execute", "exec", "invoke", "call", "dispatch", "perform", "apply"},
    {"parse", "decode", "deserialize"},
    {"serialize", "encode", "dump", "write", "emit", "render", "format"},
    {"compute", "calculate", "derive", "measure", "count"},
    {"list", "enumerate", "collect", "gather", "scan", "walk"},
    {"add", "append", "insert", "push", "register"},
    {"convert", "transform", "map", "cast", "coerce", "to"},
    {"open", "connect", "start", "init", "initialize", "setup"},
    {"close", "stop", "shutdown", "teardown", "cleanup", "disconnect", "finish"},
]
_VERB_CLASS = {v: i for i, cls in enumerate(_SYNONYM_CLASSES) for v in cls}


def _same_class(verbs: set[str]) -> bool:
    """True if two of the verbs share a synonym class."""
    seen: set[int] = set()
    for v in verbs:
        c = _VERB_CLASS.get(v)
        if c is not None:
            if c in seen:
                return True
            seen.add(c)
    return False


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=DEFAULT_ROOT)
    ap.add_argument("--top", type=int, default=20)
    args = ap.parse_args()

    corpus = scan_corpus(Path(args.root), config=None)
    lx = Lexical.over(corpus)

    # function entities with an object (>= verb + 1 token)
    funcs = [e for e in lx.named_entities() if e.kind == "function" and len(e.tokens) >= 2]

    # clone map: qualname -> clone family id
    clusters = Structure.over(corpus).clone_clusters(min_leaf_nodes=10)
    clone_of: dict[str, int] = {}
    for i, c in enumerate(clusters):
        for m in c.members:
            clone_of[m] = i

    # group functions by object-token set
    by_obj: dict[frozenset, list] = defaultdict(list)
    for e in funcs:
        verb = e.tokens[0].lower()
        obj = frozenset(t.lower() for t in e.tokens[1:])
        by_obj[obj].append((verb, e))

    raw, synonym, battery = [], [], []
    for obj, members in by_obj.items():
        verbs = {v for v, _ in members}
        files = {e.file for _, e in members}
        if len(verbs) < 2 or len(files) < 2:
            continue  # need verb divergence across modules
        raw.append((obj, members))
        if _same_class(verbs):
            synonym.append((obj, members))
        # battery: >=2 members of this group land in one clone family
        fam: dict[int, list] = defaultdict(list)
        for v, e in members:
            qn = e.locus.qualname if e.locus is not None else ""
            if qn in clone_of:
                fam[clone_of[qn]].append((v, e))
        if any(len({v for v, _ in g}) >= 2 and len({e.file for _, e in g}) >= 2
               for g in fam.values()):
            battery.append((obj, members, fam))

    print(f"root: {args.root}")
    print(f"functions (>=2 tokens): {len(funcs)}   clone families (>=10 leaves): {len(clusters)}\n")

    def _show(group, n):
        for obj, members in group[:n]:
            tag = "+".join(sorted(obj)) or "<none>"
            variants = ", ".join(f"{v}_{tag} @ {Path(e.file).stem}" for v, e in sorted(members, key=lambda ve: (ve[0], str(ve[1].file))))
            print(f"  [{tag}]  {variants}")

    print(f"== RAW: same-object / different-verb / cross-module  ({len(raw)} groups) ==")
    _show(sorted(raw, key=lambda g: -len(g[1])), args.top)

    print(f"\n== SYNONYM-class confirmed  ({len(synonym)}/{len(raw)} groups) ==")
    _show(sorted(synonym, key=lambda g: -len(g[1])), args.top)

    print(f"\n== BATTERY: synonym/verb-divergent AND co-located in a clone family "
          f"({len(battery)} groups) ==")
    if not battery:
        print("  (none — the lexical signal and clone detection do not corroborate here)")
    for obj, members, fam in battery[: args.top]:
        tag = "+".join(sorted(obj)) or "<none>"
        for fid, g in fam.items():
            if len({v for v, _ in g}) >= 2 and len({e.file for _, e in g}) >= 2:
                hits = ", ".join(f"{v}_{tag} @ {Path(e.file).stem}" for v, e in sorted(g, key=lambda ve: (ve[0], str(ve[1].file))))
                print(f"  clone#{fid}: {hits}")

    # ---- clone-first: how are real duplicate families named? -------------------
    qn_to_func = {}
    for e in funcs:
        if e.locus is not None:
            qn_to_func[e.locus.qualname] = e
    same_verb = syn_verb = unrelated = 0
    for c in clusters:
        toks = [qn_to_func[m].tokens for m in c.members if m in qn_to_func]
        verbs = {t[0].lower() for t in toks if t}
        objs = {frozenset(x.lower() for x in t[1:]) for t in toks if len(t) >= 2}
        if len(toks) < 2:
            continue
        if len(verbs) == 1:
            same_verb += 1
        elif len(objs) == 1 and _same_class(verbs):
            syn_verb += 1
        else:
            unrelated += 1
    print(f"\n== clone-first: how {len(clusters)} duplicate families are named ==")
    print(f"  identical verb (copy-paste):      {same_verb}")
    print(f"  synonym verb, same object:        {syn_verb}   <- the agent-divergence case")
    print(f"  unrelated / multi-object names:   {unrelated}")


if __name__ == "__main__":
    main()
