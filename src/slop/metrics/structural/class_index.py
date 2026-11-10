"""Corpus-wide class index + CK inheritance/coupling metrics.

CK's DIT/NOC/CBO need cross-class context (the inheritance graph and the set of known
class names), so a ``ClassIndex`` is built once over all carved classes and attached to
each ``Class`` component.

Base classes are written as simple names (``extract_superclasses`` yields ``Params``, not
``transform.grid.Params``), and simple names repeat: one corpus can hold several ``Params``
or ``Store`` classes. Each base name is therefore resolved to the *nearest* class of that
name (the same module, then the same package) and left unresolved when that is still
ambiguous. It is never merged into one class, which would hand every homonym the combined
subclass count. An unresolved base is recorded in ``ambiguous`` so a consumer can say the
numbers may undercount instead of reporting them as exact.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ...ast import NodeKind
from ...identity import ScopeId, ScopeKind


@dataclass(frozen=True)
class ClassIndex:
    parents: dict[ScopeId, tuple[Any, ...]]    # class -> its resolved direct parents
    children: dict[ScopeId, tuple[Any, ...]]   # class -> its resolved direct subclasses
    by_name: dict[str, tuple[Any, ...]]        # simple name -> every class with that name
    ambiguous: dict[ScopeId, tuple[str, ...]]  # class -> base names that matched several classes
    unattributed: dict[str, int]               # base name -> subclasses that named it but could
                                               # not be placed on any one class of that name

    @property
    def known(self) -> frozenset[str]:
        return frozenset(self.by_name)


def _enclosing(scope: Any, kind: ScopeKind) -> ScopeId | None:
    node = scope.owner
    while node is not None:
        if node.id.kind is kind:
            return node.id
        node = node.owner
    return None


def _nearest(cls: Any, candidates: list[Any],
             imports: dict[ScopeId, frozenset[ScopeId]]) -> Any | None:
    """The class ``cls`` most plausibly means by a base name, or None if undecidable.

    Not the class itself; the only candidate if there is one; otherwise, in order, the
    single candidate in the same module, the single one in a module this module imports
    (an explicit ``from b.params import Params`` beats mere proximity), then the single one
    in the same package. Two or more at the deciding step, or none at any, is ambiguous."""
    others = [c for c in candidates if c.id != cls.id]
    if not others:
        return None
    if len(others) == 1:
        return others[0]
    home_module = _enclosing(cls, ScopeKind.MODULE)
    same_module = [c for c in others if _enclosing(c, ScopeKind.MODULE) == home_module]
    if same_module:
        return same_module[0] if len(same_module) == 1 else None
    imported = imports.get(home_module, frozenset())
    via_import = [c for c in others if _enclosing(c, ScopeKind.MODULE) in imported]
    if via_import:
        return via_import[0] if len(via_import) == 1 else None
    home_package = _enclosing(cls, ScopeKind.PACKAGE)
    same_package = [c for c in others if _enclosing(c, ScopeKind.PACKAGE) == home_package]
    if same_package:
        return same_package[0] if len(same_package) == 1 else None
    return None


def build(classes: list[Any],
          imports: dict[ScopeId, frozenset[ScopeId]] | None = None) -> ClassIndex:
    """Build the index from all Class components in a corpus. ``imports`` maps a module to
    the modules it imports (resolved), so a base name can be resolved through them."""
    imports = imports or {}
    by_name: dict[str, list[Any]] = {}
    for cls in classes:
        by_name.setdefault(cls.name, []).append(cls)
    parents: dict[ScopeId, list[Any]] = {}
    children: dict[ScopeId, list[Any]] = {}
    ambiguous: dict[ScopeId, list[str]] = {}
    unattributed: dict[str, int] = {}
    for cls in classes:
        for base in cls._base_names:
            candidates = by_name.get(base, [])
            target = _nearest(cls, candidates, imports)
            if target is not None:
                parents.setdefault(cls.id, []).append(target)
                children.setdefault(target.id, []).append(cls)
            elif sum(1 for c in candidates if c.id != cls.id) > 1:
                ambiguous.setdefault(cls.id, []).append(base)
                unattributed[base] = unattributed.get(base, 0) + 1
    return ClassIndex(
        parents={k: tuple(v) for k, v in parents.items()},
        children={k: tuple(v) for k, v in children.items()},
        by_name={k: tuple(v) for k, v in by_name.items()},
        ambiguous={k: tuple(v) for k, v in ambiguous.items()},
        unattributed=unattributed,
    )


def caveats(cls: Any, idx: ClassIndex) -> tuple[str, ...]:
    """Why ``cls``'s inheritance numbers may not be exact; empty when they are."""
    notes: list[str] = []
    twins = len(idx.by_name.get(cls.name, ())) - 1
    if twins > 0:
        notes.append(f"shares its name with {twins} other class(es), so subclasses are "
                     "attributed by module, then imports, then package")
        lost = idx.unattributed.get(cls.name, 0)
        if lost:
            notes.append(f"{lost} subclass(es) naming it could not be placed on any one of "
                         f"the {twins + 1} classes of that name, so NOC may be undercounted")
    unresolved = sorted(set(idx.ambiguous.get(cls.id, ())))
    if unresolved:
        notes.append(f"base name(s) {', '.join(unresolved)} matched several classes and "
                     "were not resolved")
    return tuple(notes)


def dit(cls: Any, idx: ClassIndex) -> int:
    """Depth of Inheritance Tree — longest resolved-parent chain. Cycle-safe."""
    seen: set[ScopeId] = set()
    deepest = 0

    def walk(current: Any, depth: int) -> None:
        nonlocal deepest
        if current.id in seen:
            return
        seen.add(current.id)
        deepest = max(deepest, depth)
        for parent in idx.parents.get(current.id, ()):
            walk(parent, depth + 1)

    walk(cls, 0)
    return deepest


def noc(cls: Any, idx: ClassIndex) -> int:
    """Number of Children — direct subclasses that resolve to this class."""
    return len(idx.children.get(cls.id, ()))


def cbo(cls: Any, idx: ClassIndex) -> int:
    """Coupling Between Objects — distinct known-class references in the body.

    ``Node.walk(prune={CLASS})`` is the class-local DFS: it descends the class's
    own body but not into nested classes (each owns its own metric). References are
    counted by simple name, so homonyms count once."""
    grammar = cls._grammar
    ident_types = grammar.identifiers()
    refs: set[str] = set()
    for cur in cls._ast_node().walk(prune=frozenset({NodeKind.CLASS})):
        if cur.type in ident_types:
            text = cur.text
            if text and text[0].isupper():
                refs.add(text)
    refs &= idx.known
    for parent in idx.parents.get(cls.id, ()):
        refs.add(parent.name)
    refs.discard(cls.name)
    return len(refs)
