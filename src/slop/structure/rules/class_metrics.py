"""Class-level CK metrics — view-native (v2).

Rules (Chidamber & Kemerer 1994):

  structural.class.complexity              — WMC > 40
  structural.class.coupling                — CBO > 8
  structural.class.inheritance.depth       — DIT > 4
  structural.class.inheritance.children    — NOC > 10

All four share a corpus-level inheritance graph (``parent_map`` and
``children_map`` built once across ``structure.classes()``), so the
helper ``_class_index`` constructs that index once and the four rule
runners consume it.

Per-language superclass extraction lives on each grammar's
``extract_superclasses`` classmethod; the view's ``superclasses_of``
delegates. Go (struct + receiver methods) and Rust (struct + impl
blocks) don't fit the body-based class pattern and contribute 0 to
DIT/NOC; their CK story is a follow-up.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from slop.config.models import RuleConfig, SlopConfig
from slop.linter.slop import Slop
from slop.linter.types import RuleResult
from slop.structure.view import Structure


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
    """Build the per-corpus inheritance index used by all four rules.

    Returns (groups, parent_map, children_map, known_simple_names).
      - groups:       list of (canonical_scope, [member_scopes]) — same-name
                      Ruby openings fold into one group; non-Ruby scopes are
                      single-member groups.
      - parent_map:   simple class name → list of declared parent simple names.
      - children_map: simple parent name → list of simple child class names.
      - known:        frozenset of simple class names in the corpus.

    Parent and children maps are keyed by SIMPLE name so they aggregate
    same-name Ruby openings naturally without separate post-processing.
    """
    classes = list(structure.classes())
    parent_map: dict[str, list[str]] = {}
    children_map: dict[str, list[str]] = {}
    for s in classes:
        name = _short_name(s.qualname)
        parents = structure.superclasses_of(s)
        # Dedupe parent declarations across Ruby re-openings.
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


def run_weighted_v2(
    structure: Structure,
    rule_config: RuleConfig,
    slop_config: SlopConfig,
) -> RuleResult:
    """WMC — flag classes whose sum-of-method-CCX exceeds the threshold."""
    threshold: int = int(rule_config.params.get("threshold", 40))
    severity = rule_config.severity
    root = Path(slop_config.root).expanduser().resolve()

    groups, _, _, _ = _class_index(structure)
    findings: list[tuple[int, Slop]] = []
    for canonical, members in groups:
        # Sum WMC across all members (Ruby re-openings; singleton otherwise).
        wmc = sum(structure.weighted_methods(m) for m in members)
        if wmc > threshold:
            findings.append((wmc, _slop(
                "structural.class.complexity",
                canonical, root, severity, wmc, threshold,
                f"WMC {wmc} exceeds {threshold}",
            )))
    findings.sort(key=lambda t: -t[0])
    violations = [v for _, v in findings]
    return RuleResult(
        rule="structural.class.complexity",
        status="fail" if violations else "pass",
        violations=violations,
        summary={"classes_checked": len(groups), "violation_count": len(violations)},
        errors=[],
    )


def run_coupling_v2(
    structure: Structure,
    rule_config: RuleConfig,
    slop_config: SlopConfig,
) -> RuleResult:
    """CBO — flag classes whose distinct outbound class-references exceed the threshold."""
    threshold: int = int(rule_config.params.get("threshold", 8))
    severity = rule_config.severity
    root = Path(slop_config.root).expanduser().resolve()

    groups, _, _, known = _class_index(structure)
    findings: list[tuple[int, Slop]] = []
    for canonical, members in groups:
        # Max CBO across members (Ruby re-openings; singleton otherwise).
        cbo = max((structure.coupling(m, known) for m in members), default=0)
        if cbo > threshold:
            findings.append((cbo, _slop(
                "structural.class.coupling",
                canonical, root, severity, cbo, threshold,
                f"CBO {cbo} exceeds {threshold}",
            )))
    findings.sort(key=lambda t: -t[0])
    violations = [v for _, v in findings]
    return RuleResult(
        rule="structural.class.coupling",
        status="fail" if violations else "pass",
        violations=violations,
        summary={"classes_checked": len(groups), "violation_count": len(violations)},
        errors=[],
    )


def run_inheritance_depth_v2(
    structure: Structure,
    rule_config: RuleConfig,
    slop_config: SlopConfig,
) -> RuleResult:
    """DIT — flag classes whose inheritance chain depth exceeds the threshold."""
    threshold: int = int(rule_config.params.get("threshold", 4))
    severity = rule_config.severity
    root = Path(slop_config.root).expanduser().resolve()

    groups, parent_map, _, known = _class_index(structure)
    findings: list[tuple[int, Slop]] = []
    for canonical, _members in groups:
        # parent_map is simple-name-keyed; same DIT for every member.
        dit = structure.inheritance_depth(canonical, parent_map, known)
        if dit > threshold:
            findings.append((dit, _slop(
                "structural.class.inheritance.depth",
                canonical, root, severity, dit, threshold,
                f"DIT {dit} exceeds {threshold}",
            )))
    findings.sort(key=lambda t: -t[0])
    violations = [v for _, v in findings]
    return RuleResult(
        rule="structural.class.inheritance.depth",
        status="fail" if violations else "pass",
        violations=violations,
        summary={"classes_checked": len(groups), "violation_count": len(violations)},
        errors=[],
    )


def run_inheritance_children_v2(
    structure: Structure,
    rule_config: RuleConfig,
    slop_config: SlopConfig,
) -> RuleResult:
    """NOC — flag classes whose direct subclass count exceeds the threshold."""
    threshold: int = int(rule_config.params.get("threshold", 10))
    severity = rule_config.severity
    root = Path(slop_config.root).expanduser().resolve()

    groups, _, children_map, _ = _class_index(structure)
    findings: list[tuple[int, Slop]] = []
    for canonical, _members in groups:
        noc = structure.subclasses_count(canonical, children_map)
        if noc > threshold:
            findings.append((noc, _slop(
                "structural.class.inheritance.children",
                canonical, root, severity, noc, threshold,
                f"NOC {noc} exceeds {threshold}",
            )))
    findings.sort(key=lambda t: -t[0])
    violations = [v for _, v in findings]
    return RuleResult(
        rule="structural.class.inheritance.children",
        status="fail" if violations else "pass",
        violations=violations,
        summary={"classes_checked": len(groups), "violation_count": len(violations)},
        errors=[],
    )
