"""Agglomerations: groups of findings that are related by the code's structure.

Oizumi, Garcia et al. (ICSE 2016, "Code Anomalies Flock Together") found that a group of
inter-related anomalies indicates a design problem better than any one anomaly. A group is a
fact: the findings share an element, or their elements are joined by containment, a
reference, inheritance or an import. Whether the group has one cause is judgement, so a group
is never a violation and never changes the exit code; it is ``slop infer``'s to rule on.

A finding's elements are its ``scope`` and its ``related`` scopes. Each element's *unit* is its
class, else its top-level function, else the module or package the finding is about. Units are
related as Oizumi's elements are, not through their files: a class or function that names
another (resolved like a base class: same language, then module, import, package), a class
that inherits from another, two module-wide findings whose modules import one another, or one
finding naming both. The topologies are Oizumi's:

- ``intra-method``: findings of two or more rules on one callable;
- ``intra-class``: findings of two or more rules on one class or its methods;
- ``hierarchical``: findings of one rule on two or more classes of one inheritance tree;
- ``intra-component`` / ``cross-component``: two or more related units, all inside one package
  or spanning several.

Each group's ``lead`` is the unit the rest of the group references most (Xiao, Cai and Kazman's
leading element), else its first unit by path.
"""
from __future__ import annotations

import hashlib
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from typing import Any

from .identity import ScopeId
from .metrics.structural.class_index import references
from .scope.find import walk
from .scope.identity import ScopeKind
from .violation import Violation


class Topology(Enum):
    INTRA_METHOD = "intra-method"
    INTRA_CLASS = "intra-class"
    HIERARCHICAL = "hierarchical"
    INTRA_COMPONENT = "intra-component"
    CROSS_COMPONENT = "cross-component"


@dataclass(frozen=True)
class Agglomeration:
    """A group of related findings, the units they sit on, and the unit that leads them; for a
    hierarchical group, the one ``rule`` its findings share."""

    topology: Topology
    lead: ScopeId
    units: tuple[ScopeId, ...]
    findings: tuple[Violation, ...]
    rule: str | None = None

    @property
    def id(self) -> str:
        """Stable across runs: the topology, the lead's kind and qualified name, and the rule of a
        hierarchical group (one tree can hold a group per rule)."""
        kind, qualname = self.lead.logical
        fields = (self.topology.value, kind.value, qualname, *((self.rule,) if self.rule else ()))
        return hashlib.sha256("\0".join(fields).encode()).hexdigest()[:16]


def agglomerate(findings: list[Violation], corpus: Any) -> list[Agglomeration]:
    """Every group of two or more related findings in ``corpus``, by topology then lead path."""
    scopes = {s.id: s for s in walk(corpus)}
    structure = _Structure(corpus, scopes)
    groups = [*_contained(findings, scopes, ScopeKind.CALLABLE, Topology.INTRA_METHOD),
              *_contained(findings, scopes, ScopeKind.CLASS, Topology.INTRA_CLASS),
              *_hierarchical(findings, scopes, structure),
              *_components(findings, scopes, structure)]
    seen: set[tuple[str, ...]] = set()
    unique: list[Agglomeration] = []
    for group in groups:                    # a narrower topology already holding the same findings wins
        members = tuple(sorted(f.position for f in group.findings))
        if members not in seen:
            seen.add(members)
            unique.append(group)
    return unique


class _Structure:
    """The relations between units: references, inheritance, and imports between modules."""

    def __init__(self, corpus: Any, scopes: dict[ScopeId, Any]) -> None:
        context = corpus.context
        self._classes = context.class_index if context is not None else None
        self._graph = context.dep_graph if context is not None else None
        self._scopes = scopes
        self._definitions: dict[str, list[Any]] = defaultdict(list)
        for scope in scopes.values():
            if scope.id.kind is ScopeKind.CLASS or _is_top_level_function(scope):
                self._definitions[scope.name].append(scope)
        modules = [s for s in scopes if s.kind is ScopeKind.MODULE]
        self._imports = {m: frozenset(self._graph.efferent_nodes(m)) for m in modules} if self._graph else {}

    def parents(self, unit: ScopeId) -> tuple[ScopeId, ...]:
        return tuple(p.id for p in self._classes.parents.get(unit, ())) if self._classes else ()

    def neighbours(self, unit: ScopeId) -> set[ScopeId]:
        """The units ``unit`` names, inherits from, or (a module) imports."""
        if unit.kind is ScopeKind.MODULE:
            return set(self._imports.get(unit, ()))
        if unit.kind not in (ScopeKind.CLASS, ScopeKind.CALLABLE):
            return set()
        named = {d.id for d in references(self._scopes[unit], self._definitions, self._imports)}
        return named | set(self.parents(unit))

    def root(self, unit: ScopeId) -> ScopeId:
        """The top of ``unit``'s inheritance tree (the first parent at each step)."""
        seen = {unit}
        while (parents := self.parents(unit)) and parents[0] not in seen:
            unit = parents[0]
            seen.add(unit)
        return unit


def _is_top_level_function(scope: Any) -> bool:
    return scope.id.kind is ScopeKind.CALLABLE and scope.owner is not None and scope.owner.id.kind is ScopeKind.MODULE


def _enclosing(scope: Any, kind: ScopeKind) -> Any | None:
    while scope is not None and scope.id.kind is not kind:
        scope = scope.owner
    return scope


def _unit(scope: Any) -> Any:
    """The class an element belongs to, else its top-level function, else the element itself
    (a module or package finding)."""
    owner = _enclosing(scope, ScopeKind.CLASS)
    if owner is not None:
        return owner
    function = None
    while scope is not None and scope.id.kind is ScopeKind.CALLABLE:
        function, scope = scope, scope.owner
    return function or scope


def _elements(finding: Violation, scopes: dict[ScopeId, Any]) -> list[Any]:
    return [scopes[s] for s in (finding.scope, *finding.related) if s in scopes]


def _contained(findings: list[Violation], scopes: dict[ScopeId, Any], kind: ScopeKind,
               topology: Topology) -> list[Agglomeration]:
    """Findings of two or more rules whose element lies in one scope of ``kind``."""
    within: dict[ScopeId, list[Violation]] = defaultdict(list)
    for finding in findings:
        holder = _enclosing(scopes.get(finding.scope), kind)
        if holder is not None:
            within[holder.id].append(finding)
    return [Agglomeration(topology, holder, (holder,), tuple(group))
            for holder, group in sorted(within.items(), key=lambda item: _order(item[0]))
            if len({f.rule for f in group}) > 1]


def _hierarchical(findings: list[Violation], scopes: dict[ScopeId, Any], structure: _Structure) -> list[Agglomeration]:
    """Findings of one rule on two or more classes of one inheritance tree."""
    trees: dict[tuple[str, ScopeId], dict[ScopeId, Violation]] = defaultdict(dict)
    for finding in findings:
        if finding.scope is not None and finding.scope.kind is ScopeKind.CLASS:
            trees[(finding.rule, structure.root(finding.scope))].setdefault(finding.scope, finding)
    return [Agglomeration(Topology.HIERARCHICAL, root, tuple(sorted(members, key=_order)), tuple(members.values()), rule)
            for (rule, root), members in sorted(trees.items(), key=lambda item: (item[0][0], _order(item[0][1])))
            if len(members) > 1]


def _components(findings: list[Violation], scopes: dict[ScopeId, Any], structure: _Structure) -> list[Agglomeration]:
    """Units joined by a reference, inheritance, an import or a shared finding."""
    by_unit: dict[ScopeId, list[Violation]] = defaultdict(list)
    linked: dict[ScopeId, set[ScopeId]] = defaultdict(set)
    for finding in findings:
        units = {_unit(e).id for e in _elements(finding, scopes)}
        for unit in units:
            by_unit[unit].append(finding)
            linked[unit] |= units - {unit}
    for unit in by_unit:
        for other in structure.neighbours(unit) & by_unit.keys():
            linked[unit].add(other)
            linked[other].add(unit)
    groups: list[Agglomeration] = []
    for component in _connected(sorted(by_unit, key=_order), linked):
        if len(component) < 2:
            continue
        packages = {(_enclosing(scopes[u], ScopeKind.PACKAGE) or scopes[u]).id for u in component}
        topology = Topology.INTRA_COMPONENT if len(packages) == 1 else Topology.CROSS_COMPONENT
        members = tuple(dict.fromkeys(f for u in component for f in by_unit[u]))
        groups.append(Agglomeration(topology, _lead(component, structure), tuple(component), members))
    return groups


def _connected(units: list[ScopeId], linked: dict[ScopeId, set[ScopeId]]) -> list[list[ScopeId]]:
    seen: set[ScopeId] = set()
    components = []
    for start in units:
        if start in seen:
            continue
        component, stack = [], [start]
        seen.add(start)
        while stack:
            unit = stack.pop()
            component.append(unit)
            for other in sorted(linked[unit] - seen, key=_order):
                seen.add(other)
                stack.append(other)
        components.append(sorted(component, key=_order))
    return components


def _lead(component: list[ScopeId], structure: _Structure) -> ScopeId:
    """The unit the rest of the group references most; ties go to the first by path."""
    inside = set(component)
    referenced = {u: sum(1 for other in component if other != u and u in structure.neighbours(other) & inside)
                  for u in component}
    return min(component, key=lambda u: (-referenced[u], _order(u)))


def _order(scope: ScopeId) -> tuple[str, str]:
    return (scope.spans[0].path if scope.spans else "", scope.qualname)
