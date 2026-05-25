"""Magic literal density rule — view-native (v2).

  magic_literals  — flag functions with too many distinct
                               non-trivial numeric literals in their bodies.

A numeric literal without a symbolic name forces the reader to guess
its meaning from context. Clusters of such literals in a single
function signal that the function embeds domain logic that should
live in named constants or configuration.

Trivial constants are excluded from counting: integer values
``{-1, 0, 1, 2}`` and float values ``{-1.0, 0.0, 0.5, 1.0, 2.0, 100.0}``
appear so frequently as loop bounds / sentinels / increments that
their false-positive rate exceeds their signal.

Walk: iterates ``structure.callables()``; for each callable, descends
its body looking for numeric literal node types declared by the
callable's grammar (``Language.numeric_literal_nodes()``); skips into
nested callable definitions (each gets its own metric). Literal text
is parsed to a numeric value via ``_parse_numeric``; trivial values
drop out; the remaining literals are de-duplicated by text.

Note on category: this rule lived under ``information.*`` in v1.x but
relocated to ``*`` in v2.0 because it captures a structural
signal (missing parameterization), not a Halstead-derived information
measure. The information.* category is retired in v2.0.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from slop.linter.tags import Tag
from slop.linter.rule_config import RuleConfig
from slop.config import Config
from slop.language.grammars import LANGUAGE_BY_ID
from slop.linter.slop import Slop
from slop.linter.types import RuleResult
from slop.structure.view import Structure
from slop.linter.types import RuleDefinition


_TRIVIAL_INTS: frozenset[int] = frozenset({-1, 0, 1, 2})
_TRIVIAL_FLOATS: frozenset[float] = frozenset({-1.0, 0.0, 0.5, 1.0, 2.0, 100.0})


def run_magic_literals(
    structure: Structure,
    rule_config: RuleConfig,
    slop_config: Config,
) -> RuleResult:
    """Flag functions whose distinct non-trivial numeric literal count exceeds the threshold."""
    thresholds = rule_config.params.get("thresholds", {}) or {}
    if "function" not in thresholds:
        return RuleResult(
            rule=Tag.MAGIC_LITERALS.key, status="pass", violations=[],
            summary={"functions_analyzed": 0, "violations": 0}, errors=[],
        )
    threshold = int(thresholds.get("function", 3))
    severity = rule_config.severity
    root = Path(slop_config.root).expanduser().resolve()

    findings: list[tuple[int, Slop]] = []
    functions_analyzed = 0

    for c in structure.callables():
        functions_analyzed += 1
        language_id = structure.language_for(c)
        if language_id is None:
            continue
        lang = LANGUAGE_BY_ID.get(language_id)
        if lang is None:
            continue
        numeric_nodes = lang.numeric_literal_nodes()
        if not numeric_nodes:
            continue
        node = structure._node_by_key.get((str(c.path), c.qualname))  # noqa: SLF001
        content = structure._content_by_key.get((str(c.path), c.qualname))  # noqa: SLF001
        if node is None or content is None:
            continue
        nested_callables = lang.callable()
        body = node.child_by_field_name("body") or node
        literals = _collect_literals(body, numeric_nodes, nested_callables, content)

        # Deduplicate by text, then exclude trivials by numeric value.
        distinct_texts = sorted(set(literals))
        non_trivial = [t for t in distinct_texts if not _is_trivial(t)]
        if len(non_trivial) > threshold:
            try:
                rel = str(c.path.relative_to(root))
            except ValueError:
                rel = str(c.path)
            findings.append((len(non_trivial), Slop(
                rule=Tag.MAGIC_LITERALS.key,
                file=rel,
                line=c.line,
                symbol=c.qualname.split(".")[-1],
                message=(
                    f"'{c.qualname.split('.')[-1]}' contains {len(non_trivial)} "
                    f"distinct magic numeric literals (threshold: {threshold}): "
                    + ", ".join(non_trivial)
                ),
                severity=severity,
                value=len(non_trivial),
                threshold=threshold,
                metadata={
                    "literals": non_trivial,
                    "distinct_count": len(non_trivial),
                    "end_line": c.end_line,
                    "qualname": c.qualname,
                },
                scope="function",
            )))

    findings.sort(key=lambda t: -t[0])
    violations = [s for _, s in findings]

    return RuleResult(
        rule=Tag.MAGIC_LITERALS.key,
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "functions_analyzed": functions_analyzed,
            "violations": len(violations),
            "threshold": threshold,
        },
        errors=[],
    )


def _collect_literals(
    root_node: Any,
    numeric_nodes: frozenset[str],
    nested_callables: frozenset[str],
    content: bytes,
) -> list[str]:
    """Walk ``root_node`` collecting numeric-literal text, skipping nested callables."""
    found: list[str] = []
    stack = [root_node]
    while stack:
        cur = stack.pop()
        ctype = cur.type
        if ctype in nested_callables and cur is not root_node:
            continue
        if ctype in numeric_nodes:
            text = content[cur.start_byte:cur.end_byte].decode("utf-8", errors="replace")
            found.append(text)
        stack.extend(reversed(cur.children))
    return found


def _is_trivial(text: str) -> bool:
    """True if the literal text parses to a value in the trivial set."""
    value = _parse_numeric(text)
    if value is None:
        return False
    if isinstance(value, int):
        return value in _TRIVIAL_INTS
    return value in _TRIVIAL_FLOATS


def _parse_numeric(text: str) -> int | float | None:
    """Parse a numeric literal's text into an int or float.

    Handles common forms across the supported grammars:
      - decimal integers / floats
      - hex (``0x...``), octal (``0o...`` / leading-zero), binary (``0b...``)
      - numeric separators (``_``) — Python, Java, Rust, etc.
      - trailing type suffixes (``L`` for Java long; ``f``/``F`` float;
        ``u``/``i32`` Rust; ``i`` Go imaginary)
    Returns None if the text doesn't parse as numeric (in which case
    the caller treats the literal as non-trivial).
    """
    stripped = text.replace("_", "").strip()
    if not stripped:
        return None
    # Strip trailing type suffix letters (Java/C++ L, f, F, d, D; Rust i32, u64, etc.).
    while stripped and stripped[-1].isalpha():
        stripped = stripped[:-1]
    if stripped.endswith(("i", "j")):  # Go imaginary, Python complex
        stripped = stripped[:-1]
    if not stripped:
        return None
    # Hex / oct / bin
    try:
        if stripped.startswith(("0x", "0X")):
            return int(stripped, 16)
        if stripped.startswith(("0b", "0B")):
            return int(stripped, 2)
        if stripped.startswith(("0o", "0O")):
            return int(stripped, 8)
        # Leading-zero octal (C/Java legacy) — treat as decimal if no octal prefix.
        if "." in stripped or "e" in stripped or "E" in stripped:
            return float(stripped)
        return int(stripped)
    except ValueError:
        try:
            return float(stripped)
        except ValueError:
            return None

RULE = RuleDefinition(
    name=Tag.MAGIC_LITERALS.key,
    category=Tag.MAGIC_LITERALS.key,
    description='Distinct non-trivial numeric literals per function (magic numbers)',
    default_severity='warning',
    default_enabled=True,
    threshold_label='> 3',
    run=run_magic_literals,
    scopes=('function',),
)
