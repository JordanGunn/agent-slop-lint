"""Hidden-mutator detection — flags functions that mutate parameters in place.

Substrate-aligned port of ``out_parameters_kernel``. Iterates callables
from the Structure view and asks each grammar's ``hidden_mutators``
hook for mutation events. The substrate layer just aggregates by
callable and emits ``HiddenMutator`` records.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from slop.structure.records import HiddenMutation, HiddenMutator

if TYPE_CHECKING:
    from slop.structure.view import Structure


def compute_hidden_mutators(
    structure: Structure,
    *,
    require_type_annotation: bool = True,
) -> list[HiddenMutator]:
    """Per-callable list of detected parameter-mutation events."""
    from slop.language.grammars import LANGUAGE_BY_ID

    out: list[HiddenMutator] = []
    for c in structure.callables():
        path_str = str(c.path)
        node = structure._node_by_key.get((path_str, c.qualname))
        if node is None:
            continue
        language = structure._language_by_path.get(path_str)
        if language is None:
            continue
        lang_cls = LANGUAGE_BY_ID.get(language)
        if lang_cls is None:
            continue
        content = structure._content_by_key.get((path_str, c.qualname), b"")
        events = lang_cls.hidden_mutators(
            node, content, require_type_annotation=require_type_annotation,
        )
        if not events:
            continue
        short_name = c.qualname.rsplit(".", 1)[-1]
        mutations = tuple(
            HiddenMutation(param_name=p, method=m, line=ln) for p, m, ln in events
        )
        out.append(HiddenMutator(
            file=path_str,
            function_name=short_name,
            line=c.line,
            end_line=c.end_line,
            language=language,
            mutations=mutations,
        ))
    out.sort(key=lambda h: (-h.mutation_count, h.file, h.line))
    return out
