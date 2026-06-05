#!/usr/bin/env python
"""Measurement probe — does vocabulary affinity locate misplaced / incohesive code?

NOT a rule. A one-off measurement to decide whether the lexicon-comparison direction
earns a rule before any rule is built. Two questions over a real corpus:

  cohesion (vertical)   — how much does a module's vocabulary overlap the *rest of
                          its package*? Low overlap = a foreign body in its container.
  relocation (horizontal) — does a module's vocabulary resemble some *other, disjoint*
                          package more than its own package mates? If so, its home may
                          be wrong (the vocabulary-affinity analogue of the relocation
                          signal that died on call-affinity — no call resolution here,
                          pure identifier distribution).

Both questions reduce to comparing a module's lexicon against a *union* of scopes
(``Selection``), so this also exercises that primitive end to end.

Run (from the repo root):

  uv run python scripts/research/lexicon_affinity_probe.py --root <source-root>

Fairness note: "own context" is the module's package minus the module itself, and
every candidate "other package" is disjoint from the module (ancestor/descendant
packages are excluded), so the module is never compared against a body of code that
already contains it.
"""
from __future__ import annotations

import argparse
import math
import statistics
from collections import Counter
from pathlib import Path

from slop.lexicon import cosine, jaccard, js_similarity
from slop.scope import Selection, scan_corpus
from slop.scope.identity import ScopeKind
from slop.scope.lexicon import build_lexicon

DEFAULT_ROOT = "/home/jgodau/work/personal/slop/docs/.internal/snapshots/v1.2.0/slop"
MIN_DISTINCT = 8  # a module below this is too small for a stable vocabulary comparison


def _walk(scope, kind):
    if scope.KIND == kind:
        yield scope
    for ch in scope.children():
        yield from _walk(ch, kind)


def _freq(scope_or_selection):
    return build_lexicon(scope_or_selection).frequencies()


def _is_ranked_module(m) -> bool:
    return (
        m.name != "__init__"
        and len(set(_freq(m))) >= MIN_DISTINCT
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=DEFAULT_ROOT)
    ap.add_argument("--top", type=int, default=15)
    args = ap.parse_args()

    corpus = scan_corpus(Path(args.root), config=None)
    packages = [p for p in _walk(corpus, ScopeKind.PACKAGE)]
    modules = [m for m in _walk(corpus, ScopeKind.MODULE)]

    # Precompute each package's full (recursive) vocabulary once.
    pkg_freq = {p.qualname: (_freq(p), p) for p in packages}

    # Keyness weighting: a token's discriminating power is high when it is frequent
    # here but rare across packages. df = #packages containing the token; idf damps
    # substrate plumbing (node/name/type/file appear in every package -> ~0 weight),
    # which is exactly the confound raw Jaccard cannot see.
    n_pkgs = len(pkg_freq)
    df: Counter = Counter()
    for freq, _ in pkg_freq.values():
        df.update(set(freq))
    idf = {t: math.log(n_pkgs / d) for t, d in df.items()}

    def _w(freq):
        """tf-idf weighted vector over a frequency map (ubiquitous tokens -> ~0)."""
        return {t: c * idf.get(t, 0.0) for t, c in freq.items()}

    print(f"root: {args.root}")
    print(f"packages: {len(packages)}   modules: {len(modules)}   "
          f"(ranked modules: distinct-tokens >= {MIN_DISTINCT}, non-__init__)\n")

    rows = []
    for m in modules:
        if not _is_ranked_module(m):
            continue
        pkg = m.owner
        if pkg is None or pkg.KIND != ScopeKind.PACKAGE:
            continue
        siblings = [c for c in pkg.children() if c is not m]
        if not siblings:
            continue  # single-child package: no "rest of package" to compare against
        m_freq = _freq(m)
        own_ctx = _freq(Selection(siblings))
        own_jac = jaccard(m_freq, own_ctx)
        own_js = js_similarity(m_freq, own_ctx)
        m_w, own_w = _w(m_freq), _w(own_ctx)
        own_wcos = cosine(m_w, own_w)

        # Disjoint candidate packages only (exclude ancestors/descendants of pkg).
        best_q = best_qw = None
        best_jac = best_wcos = -1.0
        for qn, (q_freq, q) in pkg_freq.items():
            if qn == pkg.qualname:
                continue
            if qn.startswith(pkg.qualname + ".") or pkg.qualname.startswith(qn + "."):
                continue
            j = jaccard(m_freq, q_freq)
            if j > best_jac:
                best_jac, best_q = j, q
            wc = cosine(m_w, _w(q_freq))
            if wc > best_wcos:
                best_wcos, best_qw = wc, q
        delta = (best_jac - own_jac) if best_q is not None else float("nan")
        delta_w = (best_wcos - own_wcos) if best_qw is not None else float("nan")
        rows.append({
            "module": m.qualname, "distinct": len(set(m_freq)),
            "own_jac": own_jac, "own_js": own_js,
            "best_q": best_q.qualname if best_q else "-", "best_jac": max(best_jac, 0.0),
            "delta": delta,
            "own_wcos": own_wcos, "best_qw": best_qw.qualname if best_qw else "-",
            "best_wcos": max(best_wcos, 0.0), "delta_w": delta_w,
        })

    if not rows:
        print("no rankable modules.")
        return

    # ---- cohesion: lowest overlap with own package = foreign-body candidates ----
    print("== lowest cohesion (module vs rest-of-package, Jaccard asc) ==")
    print(f"{'own_jac':>7} {'own_js':>6} {'dist':>4}  module")
    for r in sorted(rows, key=lambda r: r["own_jac"])[: args.top]:
        print(f"{r['own_jac']:7.3f} {r['own_js']:6.3f} {r['distinct']:4d}  {r['module']}")

    # ---- relocation (RAW Jaccard): confounded by shared substrate vocabulary ----
    reloc = [r for r in rows if r["delta"] == r["delta"] and r["delta"] > 0]
    reloc.sort(key=lambda r: r["delta"], reverse=True)
    print(f"\n== relocation: RAW Jaccard (best disjoint package > own, by delta) =="
          f"  [{len(reloc)}/{len(rows)} fit some other package better]")
    print(f"{'delta':>6} {'own':>6} {'other':>6}  module  ->  best-fit package")
    for r in reloc[: args.top]:
        print(f"{r['delta']:6.3f} {r['own_jac']:6.3f} {r['best_jac']:6.3f}  "
              f"{r['module']}  ->  {r['best_q']}")

    # ---- relocation (KEYNESS-weighted): substrate plumbing damped by idf --------
    relw = [r for r in rows if r["delta_w"] == r["delta_w"] and r["delta_w"] > 0]
    relw.sort(key=lambda r: r["delta_w"], reverse=True)
    print(f"\n== relocation: KEYNESS-weighted tf-idf cosine (by delta_w) =="
          f"  [{len(relw)}/{len(rows)} fit some other package better]")
    print(f"{'delta_w':>7} {'own':>6} {'other':>6}  module  ->  best-fit package")
    for r in relw[: args.top]:
        print(f"{r['delta_w']:7.3f} {r['own_wcos']:6.3f} {r['best_wcos']:6.3f}  "
              f"{r['module']}  ->  {r['best_qw']}")

    # Did the substrate confound dissolve? Compare best-fit target distributions.
    raw_targets = Counter(r["best_q"] for r in reloc)
    w_targets = Counter(r["best_qw"] for r in relw)
    print("\nbest-fit target concentration (relocation candidates only):")
    print(f"  RAW Jaccard:     {dict(raw_targets.most_common(5))}")
    print(f"  KEYNESS-weighted:{dict(w_targets.most_common(5))}")

    # ---- distribution summary --------------------------------------------------
    owns = [r["own_jac"] for r in rows]
    deltas = [r["delta"] for r in rows if r["delta"] == r["delta"]]
    print("\n== summary ==")
    print(f"own-cohesion Jaccard:  mean {statistics.mean(owns):.3f}  "
          f"median {statistics.median(owns):.3f}  "
          f"min {min(owns):.3f}  max {max(owns):.3f}")
    print(f"relocation delta (raw):      >0: {sum(1 for d in deltas if d > 0)}  "
          f">0.05: {sum(1 for d in deltas if d > 0.05)}  "
          f">0.10: {sum(1 for d in deltas if d > 0.10)}  of {len(deltas)}")


if __name__ == "__main__":
    main()
