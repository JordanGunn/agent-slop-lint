"""lexical.stutter — names repeating tokens from any enclosing scope.

The hierarchy is checked top-down: every named entity (class,
function, method) is compared against package, module, and ancestor
class/function names; every body identifier inside a function is
compared against the same scope chain.

Per-level toggle parameters dial down specific levels without
splitting the rule. Defaults: all four levels enabled.

Unifies the v1.1.0 ``lexical.stutter.{namespaces, callers,
identifiers}`` split into a single hierarchy-aware rule.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from slop.linter.rule import Rule
from slop.config import Config
from slop.linter.slop import Action, Slop
from slop.linter.types import RuleResult
from slop.linter.tags import Tag
from slop.linter.types import RuleDefinition

if TYPE_CHECKING:
    from slop.lexicon.view import Lexicon


_ALL_LEVELS: frozenset[str] = frozenset({"package", "module", "class", "function"})


# Per-language scope-defining node types — these are the nodes the
# AST walker descends into to update the scope stack. Function and
# class node names match the grammars' callable / class records.
_SCOPE_NODES: dict[str, dict[str, frozenset[str]]] = {
    "python": {
        "function": frozenset({"function_definition"}),
        "class": frozenset({"class_definition"}),
    },
    "javascript": {
        "function": frozenset({"function_declaration", "function", "arrow_function",
                               "method_definition", "generator_function_declaration"}),
        "class": frozenset({"class_declaration"}),
    },
    "typescript": {
        "function": frozenset({"function_declaration", "function", "arrow_function",
                               "method_definition", "generator_function_declaration"}),
        "class": frozenset({"class_declaration"}),
    },
    "go": {
        "function": frozenset({"function_declaration", "method_declaration", "func_literal"}),
        "class": frozenset({"type_declaration"}),
    },
    "rust": {
        "function": frozenset({"function_item"}),
        "class": frozenset({"struct_item", "enum_item", "impl_item"}),
    },
    "c": {
        "function": frozenset({"function_definition"}),
        "class": frozenset(),
    },
    "cpp": {
        "function": frozenset({"function_definition", "lambda_expression"}),
        "class": frozenset({
            "class_specifier", "struct_specifier", "namespace_definition",
        }),
    },
    "ruby": {
        "function": frozenset({"method", "singleton_method", "lambda", "do_block", "block"}),
        "class": frozenset({"class", "module"}),
    },
}


_RULE = Tag.STUTTER.key

def _levels_from_config(rule_config: Rule) -> frozenset[str]:
    toggle_keys = {
        "package": "check_packages",
        "module": "check_modules",
        "class": "check_classes",
        "function": "check_functions",
    }
    return frozenset(
        level for level, key in toggle_keys.items()
        if rule_config.params.get(key, True)
    ) or _ALL_LEVELS


def _split_tokens_lower(name: str) -> set[str]:
    """Lower-cased token set for stutter comparison."""
    from slop.lexicon.view import Lexicon
    return {t.lower() for t in Lexicon.split_tokens(name)}


def _check_against_scopes(
    name: str,
    tokens_lower: set[str],
    scope_stack: list[tuple[str, str, set[str]]],
    levels: frozenset[str],
    is_entity_name: bool,
    file: str,
    line: int,
    column: int,
    language: str,
    out: list[dict[str, Any]],
    min_overlap: int,
) -> None:
    """Compare an identifier against each scope on the stack;
    emit one finding for the most-immediate stutter (deepest wins)."""
    for scope_name, scope_level, scope_tokens in reversed(scope_stack):
        if scope_level not in levels:
            continue
        if is_entity_name and scope_name == name:
            continue
        # Recursive call / self-reference: an identifier inside a function
        # whose name exactly matches the enclosing function is not a
        # naming sprawl — it's a recursive call or a same-named method
        # call (argparse `add_parser`). Skip.
        if (
            not is_entity_name
            and scope_level == "function"
            and scope_name == name
        ):
            continue
        overlap = tokens_lower & scope_tokens
        if len(overlap) >= min_overlap:
            out.append({
                "identifier": name,
                "tokens": sorted(tokens_lower),
                "file": file,
                "line": line,
                "column": column,
                "language": language,
                "scope_name": scope_name,
                "scope_level": scope_level,
                "overlap": sorted(overlap),
                "is_entity_name": is_entity_name,
            })
            return  # most-immediate match wins


def _get_name(node, content: bytes) -> str:
    """Extract a function/class node's name — mirrors grammar conventions
    for languages whose ``name`` field is not present on the node."""
    name_node = node.child_by_field_name("name")
    if name_node:
        return content[name_node.start_byte:name_node.end_byte].decode(
            "utf-8", errors="replace",
        )
    if node.type in ("lambda", "do_block", "block"):
        return "<lambda>"
    if node.type in ("method", "singleton_method"):
        saw_def = False
        saw_self = False
        saw_dot = False
        for child in node.children:
            ctype = child.type
            if ctype == "def":
                saw_def = True
                continue
            if not saw_def:
                continue
            if ctype == "self" and not saw_self:
                saw_self = True
                continue
            if ctype == "." and saw_self and not saw_dot:
                saw_dot = True
                continue
            if ctype in ("identifier", "operator"):
                return content[child.start_byte:child.end_byte].decode(
                    "utf-8", errors="replace",
                ).strip()
    if node.type in ("function_definition", "lambda_expression"):
        if node.type == "lambda_expression":
            return "<lambda>"
        declarator = node.child_by_field_name("declarator")
        for _ in range(8):
            if declarator is None:
                break
            if declarator.type == "function_declarator":
                inner = declarator.child_by_field_name("declarator")
                if inner is None:
                    break
                if inner.type in ("identifier", "field_identifier"):
                    return content[inner.start_byte:inner.end_byte].decode(
                        "utf-8", errors="replace",
                    )
                if inner.type == "qualified_identifier":
                    for c in reversed(inner.children):
                        if c.type == "identifier":
                            return content[c.start_byte:c.end_byte].decode(
                                "utf-8", errors="replace",
                            )
                    break
                if inner.type == "operator_name":
                    for c in inner.children:
                        if c.type != "operator":
                            return content[c.start_byte:c.end_byte].decode(
                                "utf-8", errors="replace",
                            ).strip()
                    break
                if inner.type == "destructor_name":
                    for c in inner.children:
                        if c.type == "identifier":
                            return "~" + content[c.start_byte:c.end_byte].decode(
                                "utf-8", errors="replace",
                            )
                    break
                break
            if declarator.type in (
                "pointer_declarator", "reference_declarator",
                "parenthesized_declarator",
            ):
                declarator = declarator.child_by_field_name("declarator")
                continue
            break
    for child in node.children:
        if child.type == "identifier":
            return content[child.start_byte:child.end_byte].decode(
                "utf-8", errors="replace",
            )
    return "<anonymous>"


def _collect_identifier_nodes(node, out) -> None:
    if node.type == "identifier" and node.child_count == 0:
        out.append(node)
    else:
        for child in node.children:
            _collect_identifier_nodes(child, out)


def _process_function_body(
    fn_node, content: bytes, rel: str, lang: str,
    scope_stack: list[tuple[str, str, set[str]]],
    levels: frozenset[str],
    findings: list[dict[str, Any]],
    min_overlap: int,
) -> None:
    body = fn_node.child_by_field_name("body") or fn_node
    identifiers: list = []
    _collect_identifier_nodes(body, identifiers)

    for ident_node in identifiers:
        name = content[ident_node.start_byte:ident_node.end_byte].decode(errors="replace")
        if name.startswith("_") and not name.startswith("__"):
            continue
        tokens_lower = _split_tokens_lower(name)
        if not tokens_lower:
            continue
        _check_against_scopes(
            name=name,
            tokens_lower=tokens_lower,
            scope_stack=scope_stack,
            levels=levels,
            is_entity_name=False,
            file=rel,
            line=ident_node.start_point[0] + 1,
            column=ident_node.start_point[1],
            language=lang,
            out=findings,
            min_overlap=min_overlap,
        )


def _scan_tree(
    root_node, content: bytes, rel: str, lang: str,
    initial_stack: list[tuple[str, str, set[str]]],
    findings: list[dict[str, Any]],
    levels: frozenset[str],
    min_overlap: int,
) -> None:
    fn_nodes = _SCOPE_NODES[lang]["function"]
    class_nodes = _SCOPE_NODES[lang]["class"]

    stack: list[tuple[object, list[tuple[str, str, set[str]]]]] = [
        (root_node, initial_stack),
    ]

    while stack:
        node, scope_stack = stack.pop()
        next_scope_stack = scope_stack

        if node.type in fn_nodes:  # type: ignore[attr-defined]
            name = _get_name(node, content)
            if name and not name.startswith("<"):
                _check_against_scopes(
                    name=name,
                    tokens_lower=_split_tokens_lower(name),
                    scope_stack=scope_stack,
                    levels=levels,
                    is_entity_name=True,
                    file=rel,
                    line=node.start_point[0] + 1,  # type: ignore[attr-defined]
                    column=node.start_point[1],  # type: ignore[attr-defined]
                    language=lang,
                    out=findings,
                    min_overlap=min_overlap,
                )
                next_scope_stack = scope_stack + [
                    (name, "function", _split_tokens_lower(name)),
                ]
            _process_function_body(
                node, content, rel, lang, next_scope_stack,
                levels, findings, min_overlap,
            )

        elif node.type in class_nodes:  # type: ignore[attr-defined]
            name = _get_name(node, content)
            if name and not name.startswith("<"):
                _check_against_scopes(
                    name=name,
                    tokens_lower=_split_tokens_lower(name),
                    scope_stack=scope_stack,
                    levels=levels,
                    is_entity_name=True,
                    file=rel,
                    line=node.start_point[0] + 1,  # type: ignore[attr-defined]
                    column=node.start_point[1],  # type: ignore[attr-defined]
                    language=lang,
                    out=findings,
                    min_overlap=min_overlap,
                )
                next_scope_stack = scope_stack + [
                    (name, "class", _split_tokens_lower(name)),
                ]

        for child in reversed(node.children):  # type: ignore[attr-defined]
            stack.append((child, next_scope_stack))


_FRAMEWORK_TOKENS: frozenset[str] = frozenset({
    # tokens whose stutter is usually framework-imposed (argparse, etc.)
    # rather than naming sloppiness
    "parser", "args", "argv",
})


def run(
    lexicon: Lexicon,
    rule_config: Rule,
    slop_config: Config,  # noqa: ARG001 — rule contract; discovery is via lexicon
) -> RuleResult:
    """Flag names that stutter with any enabled enclosing-scope level."""
    min_overlap = int(rule_config.params.get("min_overlap_tokens", 2))
    severity = rule_config.severity
    levels = _levels_from_config(rule_config)

    # Distribution signal: token file-spread. Used to classify each
    # stutter as scope-leak (high-spread overlap tokens) vs local
    # restatement (low-spread, name re-stating the immediate scope).
    from slop.lexicon.affix import UNIVERSAL_NOISE
    spread_map = {
        t: len(files)
        for t, files in lexicon.token_locations(exclude=UNIVERSAL_NOISE).items()
    }

    findings: list[dict[str, Any]] = []
    files_searched = 0

    for parse in lexicon._parses:  # noqa: SLF001 — rule consumes view substrate
        if parse.root_node is None or not parse.content:
            continue
        if parse.language not in _SCOPE_NODES:
            continue
        files_searched += 1

        rel = str(parse.path)
        initial_stack: list[tuple[str, str, set[str]]] = []
        parent_dir = parse.path.parent.name
        if parent_dir:
            initial_stack.append(
                (parent_dir, "package", _split_tokens_lower(parent_dir)),
            )
        module_name = parse.path.stem
        initial_stack.append(
            (module_name, "module", _split_tokens_lower(module_name)),
        )

        _scan_tree(
            parse.root_node, parse.content, rel, parse.language,
            initial_stack, findings, levels, min_overlap,
        )

    violations: list[Slop] = []
    for f in findings:
        kind = "name" if f["is_entity_name"] else "identifier"
        overlap_spreads = [spread_map.get(t.lower(), 0) for t in f["overlap"]]
        max_overlap_spread = max(overlap_spreads) if overlap_spreads else 0
        mean_overlap_spread = (
            sum(overlap_spreads) / len(overlap_spreads)
            if overlap_spreads else 0.0
        )
        is_framework = any(t.lower() in _FRAMEWORK_TOKENS for t in f["overlap"])

        if is_framework:
            advice = (
                "framework-imposed naming (e.g., argparse/CLI) — the "
                "stutter is structural, not a naming choice."
            )
        elif mean_overlap_spread >= 5.0:
            advice = (
                f"shared tokens are widely spread (mean {mean_overlap_spread:.0f} "
                f"files) — the {f['scope_level']} scope is leaking across "
                f"the codebase. Narrow the scope or rename the identifier."
            )
        else:
            advice = (
                f"shared tokens are local (mean spread "
                f"{mean_overlap_spread:.0f}) — the {f['scope_level']} "
                f"scope is restating its own name in the identifier. "
                f"Drop the redundant tokens from the inner name."
            )

        if is_framework:
            action = Action.ACCEPT_AS_FRAMEWORK
            prescription = (
                f"Framework-imposed naming — accept. The stutter exists "
                f"because the framework dictates the identifier name."
            )
            confidence = 0.9
        elif mean_overlap_spread >= 5.0:
            action = Action.NARROW_SCOPE
            prescription = (
                f"Rename `{f['identifier']}` or narrow the enclosing "
                f"{f['scope_level']} scope. The shared tokens {f['overlap']} "
                f"average {mean_overlap_spread:.0f}-file spread, indicating "
                f"the scope boundary is leaking across the codebase."
            )
            confidence = 0.7
        else:
            action = Action.DROP_REDUNDANT_TOKENS
            prescription = (
                f"Drop the redundant tokens {f['overlap']} from "
                f"`{f['identifier']}`. The enclosing {f['scope_level']} "
                f"`{f['scope_name']}` already carries them — the inner "
                f"name is restating its own scope."
            )
            confidence = 0.8

        violations.append(Slop(
            rule="lexical.stutter",
            file=f["file"],
            line=f["line"],
            symbol=f["identifier"],
            message=(
                f"{kind} `{f['identifier']}` stutters with "
                f"enclosing {f['scope_level']} `{f['scope_name']}` — "
                f"shared tokens {f['overlap']}. {advice}"
            ),
            severity=severity,
            value=len(f["overlap"]),
            threshold=min_overlap,
            action=action,
            prescription=prescription,
            confidence=confidence,
            metadata={
                "scope_name": f["scope_name"],
                "scope_level": f["scope_level"],
                "overlap": f["overlap"],
                "tokens": f["tokens"],
                "is_entity_name": f["is_entity_name"],
                "language": f["language"],
                "mean_overlap_spread": round(mean_overlap_spread, 1),
                "max_overlap_spread": max_overlap_spread,
                "is_framework": is_framework,
            },
        ))

    return RuleResult(
        rule="lexical.stutter",
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "files_searched": files_searched,
            "violation_count": len(violations),
            "levels_checked": sorted(levels),
        },
        errors=[],
    )

RULE = RuleDefinition(
    name=_RULE,
    category=_RULE,
    description='Names repeating tokens from any enclosing scope (package/module/class/function)',
    default_severity='warning',
    default_enabled=True,
    threshold_label='≥ 2 tokens',
    run=run,
)
