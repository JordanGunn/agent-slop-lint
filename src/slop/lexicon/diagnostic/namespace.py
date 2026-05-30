"""Namespace-aware lexical distribution functions.

These are *instrumentation* over a ``Lexicon`` view, not core lexical
API — so they live in the diagnostic subpackage as free functions taking
the view, rather than as methods inflating the ``Lexicon`` facade's WMC.
The ``vocabulary`` observation rule is their consumer.

- ``token_distribution``    — the view's global token distribution.
- ``package_distributions`` — per-package (within-namespace) distributions.
- ``concept_ownership``     — per-token owner concentration, import-gated
                              (the cross-view across-namespace axis).
"""
from __future__ import annotations

from collections import Counter
from typing import Any

from slop.lexicon.diagnostic.distribution import (
    ConceptOwnership,
    TokenDistribution,
    token_distribution as _token_distribution,
)


def _package_map(lexicon: Any) -> dict[str, str]:
    """Map each parsed file path (str) to its top-level package label.

    Common path prefix, then DESCEND into a dominant source subtree: the
    scan root is often above the package root (scanning ``src/`` where
    ``slop/`` and ``tests/`` are siblings collapses the whole package into
    one bucket). While one child directory holds ≥ 2/3 of the files, treat
    it as part of the root and descend, so grouping lands at the real
    package level. Files outside the dominant subtree are omitted. Shared
    by ``package_distributions`` and ``concept_ownership`` so both
    partition the corpus identically.
    """
    paths = [str(path) for path, _ in lexicon.by_file()]
    if not paths:
        return {}
    splits = [p.replace("\\", "/").split("/") for p in paths]
    depth = 0
    for segs in zip(*splits):
        if len(set(segs)) == 1:
            depth += 1
        else:
            break
    idx = list(range(len(paths)))
    while True:
        child_counts: Counter[str] = Counter()
        for i in idx:
            if len(splits[i]) > depth + 1:   # a directory segment, not a file
                child_counts[splits[i][depth]] += 1
        if not child_counts:
            break
        top, top_n = child_counts.most_common(1)[0]
        if top_n / sum(child_counts.values()) >= 0.66:
            idx = [i for i in idx if len(splits[i]) > depth and splits[i][depth] == top]
            depth += 1
        else:
            break
    out: dict[str, str] = {}
    for i in idx:
        rel = splits[i][depth:]
        out[paths[i]] = rel[0] if len(rel) > 1 else "<root>"
    return out


def token_distribution(
    lexicon: Any,
    *,
    top: int = 15,
    exclude: frozenset[str] = frozenset(),
    include_parameters: bool = True,
) -> TokenDistribution:
    """The view's identifier token space as a Zipfian distribution."""
    return _token_distribution(
        lexicon.frequencies(exclude=exclude, include_parameters=include_parameters),
        top=top,
    )


def package_distributions(
    lexicon: Any,
    *,
    min_distinct: int = 40,
    exclude: frozenset[str] = frozenset(),
    include_parameters: bool = True,
) -> list[tuple[str, TokenDistribution]]:
    """Per-top-level-package token distributions, ranked by hapax ratio.

    ``min_distinct`` is a hard floor on vocabulary size — per-package hapax
    inverts on small samples (a 2-token package reads 1.0). The floor is an
    admitted, *uncalibrated* cutoff; emit results as a claim-free
    observation, never a verdict.
    """
    pmap = _package_map(lexicon)
    if not pmap:
        return []
    groups: dict[str, Counter[str]] = {}
    for path, sub in lexicon.by_file():
        pkg = pmap.get(str(path))
        if pkg is None:
            continue
        groups.setdefault(pkg, Counter()).update(
            sub.frequencies(exclude=exclude, include_parameters=include_parameters),
        )

    out: list[tuple[str, TokenDistribution]] = []
    for pkg, freq in groups.items():
        dist = _token_distribution(freq)
        if dist.distinct >= min_distinct:
            out.append((pkg, dist))
    out.sort(key=lambda kv: kv[1].hapax_ratio, reverse=True)
    return out


def concept_ownership(
    lexicon: Any,
    dependency_graph: Any,
    *,
    exclude: frozenset[str] = frozenset(),
    top: int = 20,
    include_parameters: bool = True,
) -> list[ConceptOwnership]:
    """Per-token owner package + concentration, import-gated.

    A token that NAMES a package but is owned elsewhere is *displaced*;
    ``dependency_graph`` (a ``Structure.dependency_graph()`` result, with
    file→file ``efferent`` edges) gates that — if the owner package merely
    imports the eponymous package, the displacement is legitimate layering
    (``displaced_explained``). Only ``displaced_unexplained`` is signal.
    """
    pmap = _package_map(lexicon)
    if not pmap:
        return []
    packages = set(pmap.values())

    tok_pkg: dict[str, Counter[str]] = {}
    glob: Counter[str] = Counter()
    for path, sub in lexicon.by_file():
        pkg = pmap.get(str(path))
        if pkg is None:
            continue
        for tok, n in sub.frequencies(
            exclude=exclude, include_parameters=include_parameters,
        ).items():
            tok_pkg.setdefault(tok, Counter())[pkg] += n
            glob[tok] += n

    # Aggregate file→file import edges up to package→package.
    pkg_imports: dict[str, set[str]] = {}
    for src, targets in getattr(dependency_graph, "efferent", {}).items():
        src_pkg = pmap.get(src)
        if src_pkg is None:
            continue
        bucket = pkg_imports.setdefault(src_pkg, set())
        for tgt in targets:
            tgt_pkg = pmap.get(tgt)
            if tgt_pkg is not None and tgt_pkg != src_pkg:
                bucket.add(tgt_pkg)

    out: list[ConceptOwnership] = []
    for tok, _ in glob.most_common(top):
        dist = tok_pkg[tok]
        total = sum(dist.values())
        owner, owner_n = dist.most_common(1)[0]
        names_pkg = tok in packages
        displaced = names_pkg and owner != tok
        linked = displaced and tok in pkg_imports.get(owner, set())
        out.append(ConceptOwnership(
            token=tok,
            total=total,
            owner=owner,
            concentration=owner_n / total,
            package_count=len(dist),
            names_package=names_pkg,
            displaced=displaced,
            owner_imports_eponymous=linked,
        ))
    return out
