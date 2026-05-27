"""lexical.tautology — flag identifiers whose suffix restates the type annotation.

``result_dict: dict[str, int]`` — the type system already says
``dict``; the suffix is logically tautologous with the annotation.
``config_path: Path`` — same problem. The signal is purely lexical:
drop the suffix; the annotation carries the type.

Restricted to identifiers ending in a recognised type-tag suffix
(``_dict``, ``_list``, ``_path``, ``_obj``, …) AFTER underscore
parsing, to avoid false-positives like ``username``. Currently
covers Python (the most explicit annotation language); other
grammars need their own Parameter.annotation populated — see
``slop.language.base.Language.extract_parameters``.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from slop.linter.rule import Rule
from slop.config import Config
from slop.linter.slop import Slop
from slop.linter.types import RuleResult
from slop.linter.tags import Tag
from slop.linter.types import RuleDefinition

if TYPE_CHECKING:
    from slop.lexicon.view import Lexicon


DEFAULT_TAG_TO_TYPES: dict[str, frozenset[str]] = {
    "dict":  frozenset({"dict", "Dict", "Mapping", "Map"}),
    "list":  frozenset({"list", "List", "Sequence", "Iterable", "Tuple"}),
    "set":   frozenset({"set", "Set", "FrozenSet"}),
    "tuple": frozenset({"tuple", "Tuple"}),
    "str":   frozenset({"str", "String"}),
    "path":  frozenset({"Path", "PathLike", "PurePath", "PosixPath"}),
    "obj":   frozenset({"object", "Object", "Any"}),
    "data":  frozenset({"bytes", "bytearray", "Buffer"}),
    "int":   frozenset({"int", "Integer", "Long"}),
    "float": frozenset({"float", "Float", "Double"}),
    "bool":  frozenset({"bool", "Boolean"}),
}

_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def _classify(
    identifier: str, annotation: str, tags: dict[str, frozenset[str]],
) -> tuple[str | None, str | None]:
    """Return ``(suffix, matched_type)`` if the identifier's last
    underscore-separated token is a type-tag whose type set intersects
    any identifier token in ``annotation``."""
    if "_" not in identifier:
        return (None, None)
    last = identifier.rsplit("_", 1)[1].lower()
    type_set = tags.get(last)
    if type_set is None:
        return (None, None)
    annotation_idents = set(_IDENT_RE.findall(annotation))
    for matched in type_set:
        if matched in annotation_idents:
            return (last, matched)
    return (None, None)


def run_tautology(
    lexicon: Lexicon, rule_config: Rule, slop_config: Config,
) -> RuleResult:
    """Flag parameters whose name-suffix tautologically restates the annotation type."""
    raw_tags = rule_config.params.get("tag_to_types")
    tags: dict[str, frozenset[str]] = (
        {k: frozenset(v) for k, v in raw_tags.items()}
        if raw_tags else DEFAULT_TAG_TO_TYPES
    )
    severity = rule_config.severity
    root = Path(slop_config.root).expanduser().resolve() if slop_config.root else None

    violations: list[Slop] = []
    functions_checked = 0
    for c in lexicon.callables():
        language = lexicon._language_by_path.get(str(c.path))
        if language != "python":
            continue
        functions_checked += 1
        for param in c.parameters:
            if not param.annotation:
                continue
            suffix, matched = _classify(param.name, param.annotation, tags)
            if suffix is None:
                continue
            file = str(c.path)
            if root is not None:
                try:
                    file = str(Path(c.path).relative_to(root))
                except ValueError:
                    pass
            violations.append(Slop(
                rule="lexical.tautology",
                file=file,
                line=c.line,
                symbol=param.name,
                message=(
                    f"parameter `{param.name}` ends in type-tag `_{suffix}` "
                    f"matching annotation `{param.annotation}` — drop the "
                    f"suffix; the annotation carries the type"
                ),
                severity=severity,
                metadata={
                    "function": c.qualname.rsplit(".", 1)[-1],
                    "suffix": f"_{suffix}",
                    "annotation": param.annotation,
                    "matched_type": matched or "",
                    "language": language,
                },
            ))

    return RuleResult(
        rule="lexical.tautology",
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "functions_checked": functions_checked,
            "violation_count": len(violations),
        },
    )

RULE = RuleDefinition(
    name=Tag.TAUTOLOGY.key,
    category=Tag.TAUTOLOGY.key,
    description='Identifier suffixes that tautologically restate type annotations (_dict, _path, _str)',
    default_severity='warning',
    default_enabled=True,
    threshold_label='suffix matches type',
    run=run_tautology,
)
