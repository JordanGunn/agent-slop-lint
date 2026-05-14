"""Packages compute — Martin (1994) Distance from the Main Sequence.

Substrate-aligned replacement for ``slop._structural.robert.robert_kernel``.
Pulls coupling from ``Structure.dependency_graph()``, abstractness from
the grammar's ``is_abstract_scope`` classification on scope_nodes, and
package boundaries from ``Language.resolve_packages``. Emits one
``PackageMetrics`` per resolved package, zone-classified per the legacy
thresholds:

  - pain         I < 0.3 AND A < 0.3  (stable + concrete; rigid)
  - uselessness  I > 0.7 AND A > 0.7  (unstable + abstract; pure indirection)
  - warning      D' >= 0.5 (and not pain/uselessness)
  - clean        D' <  0.2
  - ok           anything else with both I and A defined
  - unknown      I or A is None (no coupling data, or no scopes classified)
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from slop.structure.records import PackageMetrics

if TYPE_CHECKING:
    from slop.structure.view import Structure


def compute_packages(structure: Structure, root: Path) -> list[PackageMetrics]:
    """Compute per-package architecture metrics across the corpus.

    Languages are processed independently: each grammar declares its
    own package-resolution rule via ``Language.resolve_packages`` and
    its own abstractness signal via ``Language.is_abstract_scope``.
    Packages without classifiable scopes still emit metrics — they
    just land in the ``unknown`` zone for abstractness.

    The dependency graph is built ONCE (corpus-wide) and aggregated
    to package-level coupling per language.
    """
    from slop.language.grammars import LANGUAGE_BY_ID

    graph = structure.dependency_graph()
    parses_by_lang: dict[str, list] = {}
    for p in structure._parses:
        parses_by_lang.setdefault(p.language, []).append(p)

    out: list[PackageMetrics] = []
    for lang_id, parses in parses_by_lang.items():
        lang_cls = LANGUAGE_BY_ID.get(lang_id)
        if lang_cls is None:
            continue

        files = [p.path for p in parses]
        packages = lang_cls.resolve_packages(root, files)
        if not packages:
            continue

        # Map abs-file-str → package name (for coupling aggregation).
        pkg_of: dict[str, str] = {}
        for pkg_name, pkg_files in packages.items():
            for f in pkg_files:
                pkg_of[str(f)] = pkg_name

        # Abstract / concrete counts per package (Na, Nc) — driven by
        # the grammar's classification of each emitted scope node.
        na_by_pkg: dict[str, int] = {p: 0 for p in packages}
        nc_by_pkg: dict[str, int] = {p: 0 for p in packages}
        for parse in parses:
            pkg_name = pkg_of.get(str(parse.path))
            if pkg_name is None:
                continue
            for scope in parse.scopes:
                # Ruby's open-class aggregation emits a synthetic
                # ``.<anonymous>`` child scope alongside the real
                # class/module scope (see Ruby post_scan_adjust). Skip
                # them so the package-level Na/Nc aren't doubled.
                if scope.qualname.endswith(".<anonymous>"):
                    continue
                node = parse.scope_nodes.get(scope.qualname)
                if node is None:
                    continue
                classification = lang_cls.is_abstract_scope(node, parse.content)
                if classification is True:
                    na_by_pkg[pkg_name] += 1
                elif classification is False:
                    nc_by_pkg[pkg_name] += 1
                # None: not counted

        # Package-level coupling (Ca, Ce): a file-level edge ``f1 → f2``
        # counts toward the source package's Ce and the target package's
        # Ca only when the two files are in DIFFERENT packages.
        ce_by_pkg: dict[str, set[str]] = {p: set() for p in packages}
        ca_by_pkg: dict[str, set[str]] = {p: set() for p in packages}
        for src, tgts in graph.efferent.items():
            src_pkg = pkg_of.get(src)
            if src_pkg is None:
                continue
            for tgt in tgts:
                tgt_pkg = pkg_of.get(tgt)
                if tgt_pkg is None or tgt_pkg == src_pkg:
                    continue
                ce_by_pkg[src_pkg].add(tgt_pkg)
                ca_by_pkg[tgt_pkg].add(src_pkg)

        for pkg_name, pkg_files in packages.items():
            ca = len(ca_by_pkg[pkg_name])
            ce = len(ce_by_pkg[pkg_name])
            na = na_by_pkg[pkg_name]
            nc = nc_by_pkg[pkg_name]
            i = _instability(ca, ce)
            a = _abstractness(na, nc)
            d = _distance(i, a)
            zone = _zone(i, a, d)
            out.append(PackageMetrics(
                name=pkg_name,
                language=lang_id,
                files=tuple(sorted(str(f) for f in pkg_files)),
                ca=ca, ce=ce, na=na, nc=nc,
                instability=i, abstractness=a, distance=d, zone=zone,
            ))

    # Sort by distance descending (worst first), then by name for stability.
    out.sort(key=lambda p: (-(p.distance or -1.0), p.name))
    return out


def _instability(ca: int, ce: int) -> float | None:
    total = ca + ce
    if total == 0:
        return None
    return ce / total


def _abstractness(na: int, nc: int) -> float | None:
    total = na + nc
    if total == 0:
        return None
    return na / total


def _distance(i: float | None, a: float | None) -> float | None:
    if i is None or a is None:
        return None
    return abs(a + i - 1.0)


def _zone(i: float | None, a: float | None, d: float | None) -> str:
    if i is None or a is None or d is None:
        return "unknown"
    if i < 0.3 and a < 0.3:
        return "pain"
    if i > 0.7 and a > 0.7:
        return "uselessness"
    if d >= 0.5:
        return "warning"
    if d < 0.2:
        return "clean"
    return "ok"
