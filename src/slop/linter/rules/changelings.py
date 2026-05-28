"""changelings — a raw literal where a named symbol already exists.

Folklore: a changeling is a substitute left in the crib in place of the
real child. Here, a raw literal value sits where a named symbol —
an enum member or a module constant whose value is identical — was
supposed to be. The named definition already exists in the codebase;
the agent re-typed the raw value instead of referencing it.

This is the classic context-window-decay failure: the symbol fell out
of the agent's context, so it spelled the value out again. The user
can't catch every recurrence by hand. slop holds the whole codebase's
symbol table in view at once — which the agent structurally cannot —
so it sees the named definition the agent forgot.

Distinct from magic_literals (which says "this value is UNNAMED").
Changelings says the opposite: "this value IS named, elsewhere, and
you used the raw literal anyway."

Detection:
1. Build a value -> symbol index across the codebase: every enum member
   value (StrEnum/IntEnum/...) and every module-level constant value.
2. Scan all string + non-trivial numeric literals. A literal whose value
   matches an indexed symbol — and which isn't that symbol's own
   definition site — is a changeling.

Confidence: enum-member matches are high (enums are the canonical
"this should be a symbol" case); module-constant matches are medium
(constants are sometimes intentionally re-literaled).

Python-only at launch (literal + enum + constant node types hardcoded);
generalises via a Language hook, same path as runts.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from slop.linter.rule import Rule
from slop.config import Config
from slop.linter.slop import Action, Slop
from slop.linter.tags import Tag
from slop.linter.types import RuleDefinition, RuleResult

if TYPE_CHECKING:
    pass


_RULE = Tag.CHANGELINGS.key

# Python enum base classes.
_ENUM_BASES: frozenset[str] = frozenset({
    "Enum", "IntEnum", "StrEnum", "IntFlag", "Flag", "ReprEnum",
})


@dataclass
class _Symbol:
    """A named definition whose value a literal might be duplicating."""
    qualname: str       # e.g. "Tag.MAGIC_LITERALS" or "DEFAULT_THRESHOLD"
    file: str
    line: int
    kind: str           # "enum_member" | "constant"


@dataclass
class _Changeling:
    """One literal occurrence that duplicates an existing symbol's value."""
    value_repr: str
    symbol: _Symbol
    file: str
    line: int


@dataclass
class _Index:
    """Value -> symbol map, plus the set of (file, line) definition sites."""
    by_value: dict[object, _Symbol] = field(default_factory=dict)
    definition_sites: set[tuple[str, int]] = field(default_factory=set)


def _literal_value(node, content: bytes) -> tuple[object, str] | None:
    """Parse a Python STRING literal node into (python_value, source_repr), or None.

    Numeric literals are deliberately NOT matched: small integers and
    common floats collide with countless unrelated sites (e.g. the int
    ``3`` coincidentally equals ``Severity.ERROR``'s value at 58 places).
    String-value coincidence is rare, so the signal is clean.
    """
    if node.type != "string":
        return None
    text = content[node.start_byte:node.end_byte].decode("utf-8", errors="replace")
    inner = None
    for ch in node.children:
        if ch.type == "string_content":
            inner = content[ch.start_byte:ch.end_byte].decode("utf-8", errors="replace")
            break
    if inner is None or len(inner) < 3:
        return None
    return (("str", inner), text)


def _superclass_names(class_node, content: bytes) -> set[str]:
    """Names in a class_definition's superclass list."""
    out: set[str] = set()
    args = class_node.child_by_field_name("superclasses")
    if args is None:
        return out
    for ch in args.children:
        if ch.type in ("identifier", "attribute"):
            out.add(content[ch.start_byte:ch.end_byte].decode("utf-8", errors="replace").split(".")[-1])
    return out


def _class_name(class_node, content: bytes) -> str:
    name_node = class_node.child_by_field_name("name")
    if name_node is None:
        return "<anon>"
    return content[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace")


def _assignment_target_and_value(stmt):
    """For an expression_statement wrapping `NAME = <value>`, return (target_node, value_node)."""
    if stmt.type != "expression_statement" or not stmt.children:
        return None
    assign = stmt.children[0]
    if assign.type != "assignment":
        return None
    target = assign.child_by_field_name("left")
    value = assign.child_by_field_name("right")
    if target is None or value is None or target.type != "identifier":
        return None
    return (target, value)


# Enums under this path are tree-sitter node-type string registries
# (Callable, Scope, Literal, Loop, ...), not semantic vocabulary. Their
# members ARE strings by nature — tree-sitter's API is string-based — so
# a raw node-type literal is a style migration, not a forgotten concept.
# Skipping them keeps changelings focused on semantic enums (Tag,
# Severity, ScopeKind) and constants.
_REGISTRY_ENUM_PATH = "language/ast/"


def _index_file(root_node, content: bytes, file_rel: str, index: _Index) -> None:
    """Walk one file's top level; register enum members + module constants.

    Enums defined under ``language/ast/`` are skipped — see
    ``_REGISTRY_ENUM_PATH``. Their node-type string members would
    generate style-migration noise, not forgotten-concept findings.
    """
    is_registry = _REGISTRY_ENUM_PATH in file_rel
    for node in root_node.children:
        # Enum class: class_definition whose bases include an enum base.
        if node.type == "class_definition":
            bases = _superclass_names(node, content)
            if bases & _ENUM_BASES and not is_registry:
                cls_name = _class_name(node, content)
                body = node.child_by_field_name("body")
                if body is not None:
                    for stmt in body.children:
                        pair = _assignment_target_and_value(stmt)
                        if pair is None:
                            continue
                        target, value = pair
                        parsed = _literal_value(value, content)
                        if parsed is None:
                            continue
                        key = parsed[0]
                        member = content[target.start_byte:target.end_byte].decode("utf-8", errors="replace")
                        line = target.start_point[0] + 1
                        index.definition_sites.add((file_rel, value.start_point[0] + 1))
                        # First definition wins; don't clobber.
                        index.by_value.setdefault(
                            key, _Symbol(f"{cls_name}.{member}", file_rel, line, "enum_member"),
                        )
            continue
        # Module-level constant: NAME = <literal> at top level.
        pair = _assignment_target_and_value(node)
        if pair is not None:
            target, value = pair
            parsed = _literal_value(value, content)
            if parsed is None:
                continue
            key = parsed[0]
            name = content[target.start_byte:target.end_byte].decode("utf-8", errors="replace")
            # Only treat UPPER_CASE / _UPPER as named constants.
            bare = name.lstrip("_")
            if not bare or not bare.isupper():
                continue
            line = target.start_point[0] + 1
            index.definition_sites.add((file_rel, value.start_point[0] + 1))
            index.by_value.setdefault(
                key, _Symbol(name, file_rel, line, "constant"),
            )


def _scan_file(root_node, content: bytes, file_rel: str, index: _Index) -> list[_Changeling]:
    """Walk one file's literals; emit changelings for value-matches."""
    out: list[_Changeling] = []
    stack = [root_node]
    while stack:
        n = stack.pop()
        if n.type in ("string", "integer", "float"):
            parsed = _literal_value(n, content)
            if parsed is not None:
                key, value_repr = parsed
                line = n.start_point[0] + 1
                if (file_rel, line) in index.definition_sites:
                    pass  # this IS a definition site, not a changeling
                else:
                    sym = index.by_value.get(key)
                    if sym is not None:
                        out.append(_Changeling(value_repr, sym, file_rel, line))
            # literals have no children worth descending
            continue
        stack.extend(n.children)
    return out


def run(
    view, rule_config: Rule, slop_config: Config,
) -> RuleResult:
    """Flag literals whose value matches an existing enum member / constant."""
    min_occurrences = int(rule_config.params.get("min_occurrences", 1))
    # A value retyped more than this many times is the codebase's working
    # vocabulary (e.g. scope-prefix words "function"/"class"/"module"
    # appearing dozens of times), not a forgotten symbol reference.
    # Forgotten references are rare and distinctive; pervasive primitives
    # are frequent. Capping isolates the former.
    max_occurrences = int(rule_config.params.get("max_occurrences", 4))
    severity = rule_config.severity
    root = Path(slop_config.root).expanduser().resolve() if slop_config.root else None

    def _rel(p) -> str:
        if root is None:
            return str(p)
        try:
            return str(Path(p).relative_to(root))
        except ValueError:
            return str(p)

    # `view` is a Structure; walk its raw parses (Python only at launch).
    parses = [
        p for p in view._parses  # noqa: SLF001 — rule consumes view substrate
        if p.language == "python" and p.root_node is not None
    ]

    # Pass 1: build the value -> symbol index across the whole corpus.
    index = _Index()
    for p in parses:
        _index_file(p.root_node, p.content, _rel(p.path), index)

    # Pass 2: scan every literal; collect changelings.
    changelings: list[_Changeling] = []
    for p in parses:
        changelings.extend(_scan_file(p.root_node, p.content, _rel(p.path), index))

    # Group by symbol qualname so a value used N times against the same
    # symbol becomes one finding carrying the occurrence list. Keying on
    # the symbol (not the literal's source text) merges quote-style
    # variants ("class" and 'class') — they're the same value.
    grouped: dict[str, list[_Changeling]] = defaultdict(list)
    for c in changelings:
        grouped[c.symbol.qualname].append(c)

    violations: list[Slop] = []
    for occ in [grouped[k] for k in sorted(grouped)]:
        if len(occ) < min_occurrences or len(occ) > max_occurrences:
            continue
        sym = occ[0].symbol
        anchor = occ[0]
        value_repr = anchor.value_repr
        confidence = 0.8 if sym.kind == "enum_member" else 0.6
        kind_phrase = (
            f"enum member `{sym.qualname}`" if sym.kind == "enum_member"
            else f"constant `{sym.qualname}`"
        )
        sites = ", ".join(f"{c.file}:{c.line}" for c in occ[:5])
        more = f" (+{len(occ) - 5} more)" if len(occ) > 5 else ""
        prescription = (
            f"Replace the literal {value_repr} with {kind_phrase} "
            f"(defined in `{sym.file}:{sym.line}`). The value already has "
            f"a name; {len(occ)} site(s) use the raw literal instead: "
            f"{sites}{more}."
        )
        violations.append(Slop(
            rule=_RULE,
            file=anchor.file,
            line=anchor.line,
            symbol=value_repr,
            message=(
                f"literal {value_repr} duplicates {kind_phrase} "
                f"(defined in `{sym.file}:{sym.line}`) — used raw at "
                f"{len(occ)} site(s). Use the existing symbol."
            ),
            severity=severity,
            value=len(occ),
            threshold=min_occurrences,
            action=Action.REPLACE_WITH_SYMBOL,
            prescription=prescription,
            confidence=confidence,
            metadata={
                "value": value_repr,
                "symbol": sym.qualname,
                "symbol_kind": sym.kind,
                "symbol_file": sym.file,
                "symbol_line": sym.line,
                "occurrences": [
                    {"file": c.file, "line": c.line} for c in occ
                ],
            },
        ))

    return RuleResult(
        rule=_RULE,
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "files_indexed": len(parses),
            "symbols_indexed": len(index.by_value),
            "changeling_count": len(violations),
        },
    )


RULE = RuleDefinition(
    name=_RULE,
    category=_RULE,
    description="Raw literals whose value matches an existing enum member or constant (use the symbol)",
    default_severity="warning",
    default_enabled=True,
    threshold_label="value matches existing symbol",
    run=run,
)
