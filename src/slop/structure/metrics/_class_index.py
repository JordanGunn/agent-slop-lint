"""Class indexing + emission helpers shared across class-scope metrics.

``_class_index`` builds the per-corpus inheritance graph (parent_map,
children_map, known set) used by every class-level rule (coupling,
inheritance.depth, inheritance.children, plus complexity at class
scope). Ruby re-openings are aggregated here so each rule sees one
logical class per simple name.

``_slop`` is the shared class-finding constructor — used by the class
metrics and the complexity-at-class-scope path.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from slop.linter.rule_config import RuleConfig
from slop.linter.slop import Slop
from slop.structure.view import Structure


def _class_threshold(rule_config: RuleConfig, default: int) -> int | None:
    """Pull the 'class' scope threshold from rule_config.

    Returns ``None`` if the rule is configured to skip the class scope
    (no ``class`` key in ``thresholds``); otherwise returns the int
    threshold (``default`` if the key value is missing).
    """
    thresholds = rule_config.params.get("thresholds", {}) or {}
    if "class" not in thresholds:
        return None
    return int(thresholds.get("class", default))


def _short_name(qualname: str) -> str:
    return qualname.split(".")[-1]


def _ruby_aggregated_groups(
    structure: Structure, classes: list[Any],
) -> list[tuple[Any, list[Any]]]:
    """Group same-simple-name Ruby class scopes into logical-class entries.

    Ruby allows ``class Foo`` to be re-opened across multiple files; each
    declaration parses as its own scope. CK metrics should aggregate
    across openings (legacy ``_aggregate_ruby_open_classes`` policy:
    sum WMC + method_count, max CBO/DIT/NOC, union superclasses).

    Returns a list of ``(canonical_scope, [all_member_scopes])`` pairs:
      - For non-Ruby scopes: each scope is its own group (member_scopes
        is a single-element list).
      - For Ruby scopes: same-simple-name scopes within the Ruby subset
        merge; canonical = first-encountered scope (preserves
        file:line attribution to the first definition).
    """
    out: list[tuple[Any, list[Any]]] = []
    ruby_by_name: dict[str, tuple[Any, list[Any]]] = {}
    for s in classes:
        lang = structure.language_for(s)
        if lang != "ruby":
            out.append((s, [s]))
            continue
        simple = _short_name(s.qualname)
        existing = ruby_by_name.get(simple)
        if existing is None:
            entry = (s, [s])
            ruby_by_name[simple] = entry
            out.append(entry)
        else:
            existing[1].append(s)
    return out


def _class_index(
    structure: Structure,
) -> tuple[
    list[tuple[Any, list[Any]]],
    dict[str, list[str]],
    dict[str, list[str]],
    frozenset[str],
]:
    """Build the per-corpus inheritance index used by all class-level rules.

    Returns (groups, parent_map, children_map, known_simple_names).
    """
    classes = list(structure.classes())
    parent_map: dict[str, list[str]] = {}
    children_map: dict[str, list[str]] = {}
    for s in classes:
        name = _short_name(s.qualname)
        parents = structure.superclasses_of(s)
        existing_parents = set(parent_map.setdefault(name, []))
        for p in parents:
            if p not in existing_parents:
                parent_map[name].append(p)
                existing_parents.add(p)
                children_map.setdefault(p, []).append(name)
    known = frozenset(parent_map.keys())
    groups = _ruby_aggregated_groups(structure, classes)
    return groups, parent_map, children_map, known


def _slop(
    rule: str,
    s: Any,
    root: Path,
    severity: str,
    value: int,
    threshold: int,
    message: str,
    metadata: dict[str, Any] | None = None,
) -> Slop:
    """Build a Slop finding for a class-scope target.

    Resolves the source path relative to ``root`` (falls back to absolute
    when the path is outside ``root``). The ``symbol`` is the class's
    short name; ``end_line`` and ``qualname`` are included as metadata.
    """
    try:
        rel = str(s.path.relative_to(root))
    except ValueError:
        rel = str(s.path)
    meta: dict[str, Any] = {"end_line": s.end_line, "qualname": s.qualname}
    if metadata:
        meta.update(metadata)
    return Slop(
        rule=rule,
        file=rel,
        line=s.line,
        symbol=_short_name(s.qualname),
        message=message,
        severity=severity,
        value=value,
        threshold=threshold,
        metadata=meta,
    )
