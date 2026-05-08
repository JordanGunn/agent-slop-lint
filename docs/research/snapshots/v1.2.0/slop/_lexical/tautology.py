"""Tautology kernel — flag identifiers whose suffix tautologically restates the type.

``result_dict: dict[str, int]`` — the type system already says
``dict``; the suffix is logically tautologous with the annotation.
``config_path: Path`` — same problem. This is a pure-lexical
refactor signal: drop the suffix; the annotation carries the type.

Restricted to identifiers ending in a recognised type-tag suffix
(``_dict``, ``_list``, ``_path``, ``_obj``, etc.) AFTER underscore
parsing, to avoid false-positives like ``username``.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from slop._lexical._naming import enumerate_functions


# Suffix → set of type-name fragments that match
DEFAULT_TAG_TO_TYPES: dict[str, frozenset[str]] = {
    "dict":   frozenset({"dict", "Dict", "Mapping", "Map"}),
    "list":   frozenset({"list", "List", "Sequence", "Iterable", "Tuple"}),
    "set":    frozenset({"set", "Set", "FrozenSet"}),
    "tuple":  frozenset({"tuple", "Tuple"}),
    "str":    frozenset({"str", "String"}),
    "path":   frozenset({"Path", "PathLike", "PurePath", "PosixPath"}),
    "obj":    frozenset({"object", "Object", "Any"}),
    "data":   frozenset({"bytes", "bytearray", "Buffer"}),
    "int":    frozenset({"int", "Integer", "Long"}),
    "float":  frozenset({"float", "Float", "Double"}),
    "bool":   frozenset({"bool", "Boolean"}),
}


@dataclass
class TypeTagHit:
    identifier: str
    file: str
    line: int
    language: str
    function: str
    suffix: str
    annotation: str
    matched_type: str


@dataclass
class TautologyResult:
    items: list[TypeTagHit] = field(default_factory=list)
    files_searched: int = 0
    functions_analyzed: int = 0
    errors: list[str] = field(default_factory=list)


# Regex that pulls the *outer* type identifier from a flat annotation
# string. ``dict[str, int]`` -> ``dict``; ``Optional[Path]`` we'll
# probe inside as well by extracting *every* identifier in the
# annotation and checking each against the suffix's type set.
_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def tautology_kernel(
    root: Path,
    *,
    languages: list[str] | None = None,
    globs: list[str] | None = None,
    excludes: list[str] | None = None,
    hidden: bool = False,
    no_ignore: bool = False,
    tag_to_types: dict[str, frozenset[str]] | None = None,
) -> TautologyResult:
    """Walk every function definition; for each annotated parameter,
    check whether the identifier suffix restates its type.

    Initial implementation covers Python (most explicit annotation
    language). Other languages: parameter typing varies wildly and the
    rule's value is lower elsewhere. Cross-language extension is a
    follow-up — the kernel API shape is stable.
    """
    tags = tag_to_types or DEFAULT_TAG_TO_TYPES
    items: list[TypeTagHit] = []
    files_set: set[str] = set()
    fn_count = 0

    for ctx in enumerate_functions(
        root,
        languages=languages, globs=globs, excludes=excludes,
        hidden=hidden, no_ignore=no_ignore,
    ):
        fn_count += 1
        files_set.add(ctx.file)
        if ctx.language != "python":
            continue
        items.extend(_check_python_params(ctx, tags))

    return TautologyResult(
        items=items,
        files_searched=len(files_set),
        functions_analyzed=fn_count,
        errors=[],
    )


def _check_python_params(ctx, tags) -> list[TypeTagHit]:
    """Iterate parameters with annotations on a Python function node."""
    out: list[TypeTagHit] = []
    params = ctx.node.child_by_field_name("parameters")
    if params is None:
        return out
    for child in params.children:
        if child.type != "typed_parameter":
            continue
        # typed_parameter: identifier ":" type
        ident_node = None
        type_node = child.child_by_field_name("type")
        for sub in child.children:
            if sub.type == "identifier" and ident_node is None:
                ident_node = sub
                break
        if ident_node is None or type_node is None:
            continue
        ident = ctx.content[ident_node.start_byte:ident_node.end_byte].decode(
            "utf-8", errors="replace",
        )
        annotation = ctx.content[type_node.start_byte:type_node.end_byte].decode(
            "utf-8", errors="replace",
        )
        suffix, matched = _classify(ident, annotation, tags)
        if suffix is None:
            continue
        out.append(TypeTagHit(
            identifier=ident, file=ctx.file,
            line=ident_node.start_point[0] + 1,
            language=ctx.language, function=ctx.name,
            suffix=f"_{suffix}", annotation=annotation,
            matched_type=matched or "",
        ))
    return out


def _classify(
    identifier: str,
    annotation: str,
    tags: dict[str, frozenset[str]],
) -> tuple[str | None, str | None]:
    """Return ``(suffix, matched_type)`` if the identifier's last
    underscore-separated token matches a tag whose type set overlaps
    the annotation's identifier tokens. Else ``(None, None)``."""
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
